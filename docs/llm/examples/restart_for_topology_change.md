# Example: Restart for Session Changes

```bash
curl -s -X POST -H "Authorization: Bearer $SEINE_API_TOKEN" http://127.0.0.1:9977/v1/miner/stop
curl -s -X POST -H "Authorization: Bearer $SEINE_API_TOKEN" http://127.0.0.1:9977/v1/miner/start -H 'content-type: application/json' -d '{"threads":2}'
```
