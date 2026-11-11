Invoke-RestMethod -Uri 'http://127.0.0.1:8188/free' -Method Post -ContentType 'application/json' -Body '{"unload_models":true,"free_memory":true}'
'GPU model unload requested; HTTP server stays running.'
