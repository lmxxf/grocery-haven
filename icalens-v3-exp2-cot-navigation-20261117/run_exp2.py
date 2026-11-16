from common_exp2 import *
import sys,time,importlib.util,traceback,gc
sys.path.insert(0,str(V3))
def module(name,file):
 spec=importlib.util.spec_from_file_location(name,R/file);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def main():
 import torch
 from model_loader import load_model
 torch.set_num_threads(8);torch.set_float32_matmul_precision('highest');torch.manual_seed(0)
 if not(R/'calibration.json').exists():module('calibrate','calibrate_exp2.py').run()
 tok,model=load_model();append('Step 2｜27B一次驻留开始','复用v3原逐块FP8→BF16加载器。后续生成、缓存路径捕获、补跑与词表核对在这一份模型驻留期间完成。')
 records=[];queue=read(R/'cases.json');rounds=0
 while True:
  while queue:
   case=queue.pop(0)
   while True:
    try:
     gen=module('generation','generate_exp2.py');record=gen.generate(model,tok,case);records.append(record);save('completed_cases.json',[x['id']for x in records]);
     if len(records)==1:gen.cached_replay_check(model,tok,record)
     break
    except Exception:
     error=traceback.format_exc();(R/'error.log').write_text(error);print(error,flush=True);save('progress.json',dict(stage='needs_repair',case=case['id'],model_resident=True));(R/'resume.flag').unlink(missing_ok=True)
     while not(R/'resume.flag').exists():time.sleep(2)
  while not(R/'analysis.ready').exists():time.sleep(2)
  try:
   extra=module('navigation_analysis','analyze_exp2.py').run(model,tok,records,rounds)
   if extra and rounds<2:queue=extra;rounds+=1;save('extra_cases.json',extra);continue
   break
  except Exception:
   error=traceback.format_exc();(R/'analysis_error.log').write_text(error);print(error,flush=True);(R/'analysis.ready').unlink(missing_ok=True);save('progress.json',dict(stage='analysis_needs_repair',model_resident=True))
 save('progress.json',dict(stage='complete',cases=len(records)));append('收工状态｜数据与模型生命周期','本轮全部生成与补跑完成，进程退出后释放GPU模型。没有后台等待任务。')
if __name__=='__main__':main()
