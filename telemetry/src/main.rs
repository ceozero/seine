use axum::{
    extract::{DefaultBodyLimit, State},
    http::StatusCode,
    routing::{get, post},
    Json, Router,
};
use seine_telemetry::{Report, MAX_BODY_BYTES};
use std::{
    collections::HashMap,
    env,
    net::SocketAddr,
    sync::{Arc, Mutex},
    time::{Duration, Instant},
};
use tokio_postgres::{Client, NoTls};

#[derive(Clone)]
struct App {
    db: Arc<tokio::sync::Mutex<Option<Client>>>,
    db_config: tokio_postgres::Config,
    // No IP addresses: global admission and per-installation quotas bound work.
    admission: Arc<Mutex<Admission>>,
}

struct Admission {
    since: Instant,
    count: u32,
    installations: HashMap<String, Instant>,
}

impl Admission {
    fn admit(&mut self, id: &str) -> bool {
        let now = Instant::now();
        if now.duration_since(self.since) >= Duration::from_secs(1) {
            self.since = now;
            self.count = 0;
        }
        if self.count >= 20 {
            return false;
        }
        self.count += 1;
        if self
            .installations
            .get(id)
            .is_some_and(|last| now.duration_since(*last) < Duration::from_secs(300))
        {
            return false;
        }
        if self.installations.len() >= 100_000 {
            self.installations
                .retain(|_, last| now.duration_since(*last) < Duration::from_secs(300));
            if self.installations.len() >= 100_000 {
                return false;
            }
        }
        self.installations.insert(id.to_owned(), now);
        true
    }
}

async fn ingest(State(app): State<App>, Json(report): Json<Report>) -> StatusCode {
    if !report.validate() {
        return StatusCode::UNPROCESSABLE_ENTITY;
    }
    if !app
        .admission
        .lock()
        .unwrap_or_else(|e| e.into_inner())
        .admit(&report.installation_id)
    {
        return StatusCode::TOO_MANY_REQUESTS;
    }
    // Reject overload rather than accumulating blocked Postgres tasks.
    let Ok(permit) = DB_SLOTS.try_acquire() else {
        return StatusCode::SERVICE_UNAVAILABLE;
    };
    let result = async {
        let payload = serde_json::to_value(&report).map_err(|_| ())?;
        let mut guard = app.db.lock().await;
        if guard.as_ref().is_none_or(Client::is_closed) {
            *guard = Some(connect(&app.db_config).await.map_err(|_| ())?);
        }
        let db = guard.as_ref().ok_or(())?;
        db.execute(
            "INSERT INTO telemetry_reports (installation_id, report_id, payload) VALUES ($1, $2, $3) ON CONFLICT (report_id) DO NOTHING",
            &[&report.installation_id, &report.report_id, &payload],
        ).await.map_err(|_| ())?;
        Ok::<_, ()>(())
    }.await;
    drop(permit);
    match result {
        Ok(()) => StatusCode::NO_CONTENT,
        _ => StatusCode::SERVICE_UNAVAILABLE,
    }
}

static DB_SLOTS: tokio::sync::Semaphore = tokio::sync::Semaphore::const_new(8);

async fn connect(config: &tokio_postgres::Config) -> Result<Client, tokio_postgres::Error> {
    let (client, connection) = config.connect(NoTls).await?;
    tokio::spawn(async move {
        let _ = connection.await;
    });
    Ok(client)
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Intended for a local/private database. Use a local TLS proxy for a remote DB.
    let database_url = env::var("TELEMETRY_DATABASE_URL")?;
    let mut db_config: tokio_postgres::Config = database_url.parse()?;
    db_config.connect_timeout(Duration::from_secs(5));
    db_config.options("-c statement_timeout=5000");
    let db = connect(&db_config).await?;
    db.batch_execute(include_str!("schema.sql")).await?;
    let app = App {
        db: Arc::new(tokio::sync::Mutex::new(Some(db))),
        db_config,
        admission: Arc::new(Mutex::new(Admission {
            since: Instant::now(),
            count: 0,
            installations: HashMap::new(),
        })),
    };
    let maintenance = app.clone();
    tokio::spawn(async move {
        let mut interval = tokio::time::interval(Duration::from_secs(3600));
        loop {
            interval.tick().await;
            let app = maintenance.clone();
            // Bounded retention batches avoid long table locks.
            let guard = app.db.lock().await;
            if let Some(db) = guard.as_ref() {
                let _ = db.execute("DELETE FROM telemetry_reports WHERE report_id IN (SELECT report_id FROM telemetry_reports WHERE received_at < now() - interval '30 days' LIMIT 100000)", &[]).await;
            }
        }
    });
    let routes = Router::new()
        .route("/healthz", get(|| async { StatusCode::NO_CONTENT }))
        .route("/v1/reports", post(ingest))
        .layer(DefaultBodyLimit::max(MAX_BODY_BYTES))
        .with_state(app);
    let bind: SocketAddr = env::var("TELEMETRY_BIND")
        .unwrap_or_else(|_| "127.0.0.1:9080".into())
        .parse()?;
    let listener = tokio::net::TcpListener::bind(bind).await?;
    eprintln!("telemetry collector listening on {bind}; request logging disabled");
    axum::serve(listener, routes)
        .with_graceful_shutdown(async {
            let _ = tokio::signal::ctrl_c().await;
        })
        .await?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn rate_limit_bounds_global_and_installation_ingestion() {
        let mut a = Admission {
            since: Instant::now(),
            count: 0,
            installations: HashMap::new(),
        };
        assert!(a.admit("one"));
        assert!(!a.admit("one"));
        for i in 0..18 {
            assert!(a.admit(&i.to_string()));
        }
        assert!(!a.admit("over-global-limit"));
        a.since -= Duration::from_secs(2);
        assert!(a.admit("new-window"));
        assert!(!a.admit("one"));
    }
}
