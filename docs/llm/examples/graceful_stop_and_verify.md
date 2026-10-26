# Example: Graceful Stop and Verify

```bash
curl -s -X POST -H "Authorization: Bearer $SEINE_API_TOKEN" http://127.0.0.1:9977/v1/miner/stop -H 'content-type: application/json' -d '{"wait_ms":15000}'
curl -s -H "Authorization: Bearer $SEINE_API_TOKEN" http://127.0.0.1:9977/v1/runtime/state
```
