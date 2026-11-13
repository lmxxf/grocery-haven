#!/usr/bin/env python3
import json,subprocess,tempfile,time,sys,pathlib
payload=json.loads(sys.argv[1]);payload['id']=str(time.time_ns())
with tempfile.TemporaryDirectory() as tmp:
 p=pathlib.Path(tmp)/'command.json';p.write_text(json.dumps(payload))
 subprocess.run(['scp',str(p),'rtx5090:C:/Temp/egpu_probe/desktop_next.json'],check=True,stdout=subprocess.DEVNULL)
 subprocess.run(['ssh','rtx5090','powershell -NoProfile -Command "Move-Item -Force C:\\Temp\\egpu_probe\\desktop_next.json C:\\Temp\\egpu_probe\\desktop_command.json"'],check=True,stdout=subprocess.DEVNULL)
 for i in range(20):
  result=subprocess.run(['ssh','rtx5090','powershell -NoProfile -Command "Get-Content C:\\Temp\\egpu_probe\\desktop_result.json -Raw -ErrorAction SilentlyContinue"'],capture_output=True,text=True,encoding="utf-8",errors="replace")
  try:
   data=json.loads(result.stdout.lstrip('\ufeff'))
   if data['id']==payload['id']:
    print(json.dumps(data,ensure_ascii=False));sys.exit(0 if data['ok'] else 1)
  except (ValueError,KeyError):pass
  time.sleep(.25)
 raise SystemExit('desktop command timed out')
