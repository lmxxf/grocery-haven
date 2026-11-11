import json
from pathlib import Path
R=Path(__file__).resolve().parent;rows=[]
subjects=[('cat','猫'),('dog','狗'),('teacher','老师'),('doctor','医生'),('farmer','农民'),('student','学生'),('engineer','工程师'),('artist','画家')]
patterns=[('The {} walked beside the river.','{}沿着河边散步。'),('The {} opened the blue door.','{}打开了蓝色的门。'),('Yesterday the {} read a book.','昨天{}读了一本书。'),('The {} drank water after lunch.','{}午饭后喝了水。'),('The {} waited at the station.','{}在车站等待。'),('The {} looked at the mountain.','{}望向那座山。'),('The {} rested under the tree.','{}在树下休息。'),('Today the {} returned home.','今天{}回到了家。')]
for i,(en,zh)in enumerate(subjects):
 for j,(a,b)in enumerate(patterns):
  for lang,text in [('en',a.format(en)),('zh',b.format(zh))]:rows.append({'id':f'parallel_{i}_{j}_{lang}','group':'parallel','pair':f'{i}_{j}','lang':lang,'split':'fit'if i<6 else'heldout','text':text})
poly=[('bank_finance','The customer deposited cash at the bank'),('bank_river','The fisherman sat on the grassy river bank'),('bank_finance','She withdrew her savings from the bank'),('bank_river','The flood eroded the muddy river bank'),('bank_finance','The company borrowed money from the bank'),('bank_river','The ducks nested beside the river bank'),('apple_fruit','For breakfast she sliced a fresh apple'),('apple_company','The new iPhone was designed by apple'),('apple_fruit','The farmer picked a ripe red apple'),('apple_company','The Mac computer was manufactured by apple'),('苹果水果','早餐时她洗净了一个红富士苹果'),('苹果公司','发布会展示了新款手机，制造商是苹果'),('苹果水果','果园里刚采摘了一筐新鲜苹果'),('苹果公司','这款新电脑的制造商是苹果')]
seen={}
for i,(label,text)in enumerate(poly):
 seen[label]=seen.get(label,0)+1
 rows.append({'id':f'poly_{i}','group':'polysemy','label':label,'text':text,'split':'fit'if seen[label]%2 else'heldout'})
(R/'probes.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2))
print(len(rows),'probes')
