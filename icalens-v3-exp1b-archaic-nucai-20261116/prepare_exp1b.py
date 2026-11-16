"""Build frozen, source-verified causal-prefix probes. No generated classical quotations."""
import json,re,hashlib,sys
from pathlib import Path
from bs4 import BeautifulSoup
R=Path(__file__).resolve().parent
HEAVY=Path('/home/lmxxf/work/ica-lens-qwen38-27b-v3/experiments/exp1b_archaic_nucai')
MODEL='/home/lmxxf/work/models/Qwen3.8-27B-FP8'
def save(name,data): (R/name).write_text(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False))
def read(name):return json.loads((R/name).read_text())
def compact(s):return re.sub(r'\s+','',s)
INTRO='''At Cambridge, a small seminar in classical Chinese documentary studies meets in a quiet room beside the library. The students have placed a transcription and a photographic reproduction on the table. Their task today is to read an old document in the order in which its words appear, keeping the language of the surrounding discussion in English. The instructor first describes the material object: the arrangement of columns, the spacing of the written lines, the visible punctuation added by later editors, and the relation between the printed page and its manuscript witnesses. No translation or lexical gloss has yet been supplied.

One student records the shelf reference while another compares the beginning of the transcription with the reproduction. They note where a heading ends and where the continuous text begins. A third student checks the sequence against a second edition, but leaves differences in the margin rather than inserting explanatory words into the passage. Everyone agrees to distinguish the wording of the document from modern commentary. The group will not turn the text into a contemporary conversation or ask its historical speaker to address a present-day audience.

The instructor asks the readers to keep track of the date, the addressee, the kind of document, and the conventions used by the writer. These are questions about the circumstances of transmission and reading, not definitions of particular expressions. The participants discuss how a copyist might mark the end of a section, how a compiler might place one item beside another, and how later printing could change the appearance of the page without changing the order of its words.

For the next exercise the class will read the original Chinese directly. There will be no English paraphrase between its sentences. The transcription is treated as a historical witness, and every word is to be read with the preceding text still in view. The reader pauses at the end of the following excerpt; no subsequent sentence has been provided. What follows is the documentary text itself, without an answer key, a vocabulary list, or a statement of its interpretation.

'''

def build():
 from transformers import AutoTokenizer
 tok=AutoTokenizer.from_pretrained(MODEL,local_files_only=True)
 probes=[];pairs=[];samples=[];bykey={};verification=[]
 def add(prefix,target,**meta):
  text=prefix+target;key=(text,target)
  if key in bykey:return bykey[key]
  suffix=tok.encode(target,add_special_tokens=False);ids=tok.encode(prefix,add_special_tokens=False)+suffix
  assert tok.decode(ids)==text and not(set(ids)&set(tok.all_special_ids))
  ident=len(probes);bykey[key]=ident;probes.append(dict(id=ident,text=text,target=target,target_start=len(ids)-len(suffix),target_ids=suffix,target_tokens=tok.convert_ids_to_tokens(suffix),input_ids=ids,token_count=len(ids),**meta));return ident
 def contrast(group,frame,bad,good,text,split='fit'):
  assert '卑鄙' not in text and '奴才' not in text
  a=add(text,bad,kind='reference',group=group,split=split);b=add(text,good,kind='reference',group=group,split=split)
  pairs.append(dict(group=group,a=a,b=b,frame=frame,cluster=bad+'/'+good,split=split))
 frames=['关于这位人物的处世作风，人们查阅了许多独立材料，最后采用的评价词是','在那篇讨论个人品格的文章结尾，作者没有罗列细节，而是用一个词概括为','经过对日常言行的长期观察，熟悉情况的人给出的描述是','这份人物评论比较了前后的各种表现，对其处世方式的总结是','读完这部传记以后，讨论小组对于此人品性的用词是','在一段不涉及职务高低的谈话里，大家评价这个人的为人是','他在笔记中反复斟酌了措辞，对这个人的整体评价是','两位评论者各自看过证词以后，对其品行写下的判断都是']
 for i,f in enumerate(frames):contrast('Mod_Moral_Beibi',i,'卑鄙',['坦荡','正直','磊落','高尚'][i%4],f)
 moral=[('无耻','高尚'),('下流','正直'),('阴险','坦荡'),('龌龊','磊落'),('恶毒','善良'),('卑劣','高洁'),('奸诈','诚实'),('虚伪','真诚')]
 for i,(a,b) in enumerate(moral):contrast('Moral_Nonliteral',i,a,b,frames[i])
 for i,(a,b) in enumerate([('恶劣','优良'),('歹毒','仁厚'),('厚颜无耻','光明磊落'),('损人利己','公正无私')]):contrast('Moral_Nonliteral',8+i,a,b,frames[i],split='heldout')
 status=[('出身微贱','出身显贵'),('布衣寒门','豪门望族'),('地位卑微','位高权重'),('寒门小户','高门大族'),('平民百姓','王公贵族'),('身份低微','身份尊贵'),('贫寒人家','富贵之家'),('草民布衣','达官显宦')]
 for i,(a,b) in enumerate(status):contrast('Status_Humble',i,a,b,'这段生平材料只说明身份阶层而不评价品格，关于此人的家庭背景或社会地位，所记的是')
 r1=[('谄媚','不卑不亢'),('摇尾乞怜','铮铮铁骨'),('卑躬屈膝','堂堂正正'),('走狗','志士'),('舔狗','君子'),('下贱','尊严'),('阿谀奉承','刚正不阿'),('奴颜婢膝','昂首挺胸')]
 for i,(a,b) in enumerate(r1):contrast('R1_Humiliation',i,a,b,frames[i])
 for i,(a,b) in enumerate([('低声下气','理直气壮'),('趋炎附势','坚持原则'),('屈膝求荣','自尊自立'),('奴性十足','有骨气')]):contrast('R1_Humiliation',8+i,a,b,frames[i],split='heldout')
 r2=[('微臣','邻居'),('臣等','我们'),('叩首','问候'),('圣安','平安'),('陛下','先生'),('奉旨','约定'),('奏折','家书'),('谢恩','道谢')]
 for i,(a,b) in enumerate(r2):contrast('R2_Court',i,a,b,'研究者正在摘录材料中的常用称谓和行事用语，这一行出现的词是')
 # Unannotated SGZ: remove Pei Songzhi's small-font notes, not arbitrary text spans.
 soup=BeautifulSoup((R/'sources/sanguozhi.raw').read_text(),'html.parser');node=max(soup.select('.mw-parser-output'),key=lambda x:len(x.get_text()))
 for x in node.select('small,script,style,.noprint,.ws-noexport,.mw-editsection'):x.decompose()
 sgz=compact(node.get_text('\n',strip=True));begin=sgz.index('诸葛亮字孔明');at=sgz.index('先帝不以臣卑鄙',begin);end=at+len('先帝不以臣')
 w2=sgz[begin:end];w1=sgz[sgz.index('先帝创业未半',begin):end];w0='先帝不以臣'
 assert '卑鄙' not in w2
 wraps={'W0':w0,'W1':w1,'W2':w2,'W3a':INTRO+'The item for this reading is a third-century memorial attributed to Zhuge Liang, a minister of the Han state.\n\n'+w0,'W3b':INTRO+'The item for this reading is a third-century memorial attributed to Zhuge Liang, a minister of the Han state.\n\n'+w1}
 cal=[]
 for w,prefix in wraps.items():
  for target in ['卑鄙','微贱','浅陋','愚钝']:
   ident=add(prefix,target,kind='calibration',wrapper=w,source='SGZ35',is_original=target=='卑鄙',substitution=None if target=='卑鄙' else '卑鄙→'+target)
   cal.append(dict(wrapper=w,target=target,id=ident))
 save('calibration_design.json',dict(wrappers={w:dict(chars=len(p),tokens=len(tok.encode(p,add_special_tokens=False))) for w,p in wraps.items()},english_intro_words=len(INTRO.split()),calibration=cal))
 # Select actual occurrences by immutable chapter+character offsets; no invented quotations.
 inventory=read('honglou_occurrence_inventory.json')
 A2ids=[3,6,7,63,65,76,87,88,131,136]
 Bids=[2,14,21,26,27,46,60,61,73,121]
 def sample(group,source,text,pos,doc_id,**extra):
  assert text[pos:pos+2]=='奴才';left=text[max(0,pos-1300):pos].replace('上一回\n回目录\n下一回\n','');short=text[max(0,pos-180):pos].replace('上一回\n回目录\n下一回\n','')
  verification.append(dict(group=group,source=source,doc_id=doc_id,position=pos,left_chars=len(left),left_tail=left[-180:],target='奴才',right_for_audit_only=text[pos:pos+130],**extra))
  split='heldout' if int(hashlib.sha256(doc_id.encode()).hexdigest()[:8],16)%3==0 else 'fit'
  wrappers={'short':short,'W2_native':left,'W2_shared':w2+'\n\n'+short,'W3':INTRO+'The item below is a historical document preserved for documentary reading.\n\n'+short}
  for wrapper,prefix in wrappers.items():
   targets=['奴才','臣'] if group=='A1' else ['奴才','小的','下官','我'] if group=='A2' else ['奴才']
   for target in targets:
    ident=add(prefix,target,kind='historical',group=group,wrapper=wrapper,doc_id=doc_id,source=source,split=split,is_original=target=='奴才',substitution=None if target=='奴才' else '奴才→'+target,**extra)
    samples.append(dict(group=group,wrapper=wrapper,target=target,id=ident,doc_id=doc_id,source=source,split=split,**extra))
 for group,ids in [('A2',A2ids),('B',Bids)]:
  for i in ids:
   x=inventory[i];text=(R/'sources/honglou'/f"{x['chapter']:03d}.txt").read_text();pos=x['position'];# The inventory position is checked against the frozen original source.
   sample(group,f"https://zh.wikisource.org/zh-hans/紅樓夢/第{x['chapter']:03d}回",text,pos,'HLM_ch'+str(x['chapter']),sample_id='HLM_'+str(i),chapter=x['chapter'],inventory_id=i)
 # Ten memorial occurrences, including Yang's original crossed-out opening checked visually.
 docs=read('caojia_documents.json');by_number={x['number']:x for x in docs}
 selected=['十八','一百五十五','一百八十九','一百九十四','一百九十六','一百九十八','二百一十六','二百二十三','二百七十三','二百八十六']
 # Nine main memorials + Yang = ten. #18 is Manchu-to-Chinese translation and is separate audit sample.
 for number in selected:
  d=by_number[number];text=d['text'];heading=number+d['title'];assert text.startswith(heading);text=text[len(heading):];date_end=text.find('日');text=text[date_end+1:] if 0<=date_end<40 else text;# Remove editorial title/date from model input; keep both in provenance.
  body_start=min([m.start() for m in re.finditer(r'(?:总管内务府谨题|江西巡抚奴才|奴才李煦|江宁织造|苏州织造)',text[len(number)+len(d['title']):])],default=0)
  # Prefer a later self-reference, so causal left context actually contains the memorial's content.
  positions=[m.start() for m in re.finditer('奴才',text)];valid=[p for p in positions if p>=min(180,len(text)//2)]
  pos=valid[len(valid)//2] if valid else positions[-1]
  if number=='十八':
   q=text.index('查江宁织造');text=text[q:text.index('曹寅一年之本银',q)] if '曹寅一年之本银' in text[q:] else text[q:q+500];pos=[m.start() for m in re.finditer('奴才',text)][-1]
   sample('A1_translation_audit','https://ctext.org/wiki.pl?chapter=747644&if=gb',text,pos,'Caojia_'+number,sample_id='Caojia_'+number,document_title=d['title'],translation=True)
  else:sample('A1','https://pdf.fengshui86.com/wzpdf/9203881.pdf',text,pos,'Caojia_'+number,sample_id='Caojia_'+number,document_title=d['title'],translation=False)
 # Yang's target is at the opening. Never move the right-hand memorial body to its left.
 yang='湖广总督奴才杨宗仁叩首恭请皇上圣安';sample('A1','https://theme.npm.edu.tw/Academic/ChineseArtDownload.ashx?bid=5296&eid=0',yang,yang.index('奴才'),'Yang_1723_04_05',sample_id='Yang_022688',document_title='杨宗仁请安折，雍正元年四月初五日，故宫022688',translation=False,manual_facsimile_verified=True)
 # An authenticated imperial insult: the suggested "不知好歹之奴才" was not substituted for an unverified quotation.
 imperial=(R/'sources/imperial063.txt').read_text();pos=imperial.index('奴才');sample('B_imperial','https://zh.wikisource.org/zh-hans/上諭内閣 (四庫全書本)/卷063',imperial,pos,'Imperial_1727_11',sample_id='Imperial063',document_title='雍正五年十一月上谕内阁卷63：包衣下贱奴才')
 # Ten genuine modern critical occurrences; cluster by work, not repeated target appearances.
 choices=[('luxun_duomin',[2,3,4],'我談「墮民」'),('luxun_manyu',[0],'漫與'),('luxun_shanghai',[0],'上海文藝之一瞥'),('luxun_yanyu',[0,1,2],'諺語'),('luxun_nucai',[0,2],'隔膜')]
 for fname,indices,title in choices:
  text=(R/'sources'/f'{fname}.txt').read_text();positions=[m.start() for m in re.finditer('奴才',text)]
  for j in indices:sample('C','https://zh.wikisource.org/zh-hans/'+title,text,positions[j],fname,sample_id=fname+'_'+str(j),document_title=title)
 # Genuine Nian and Ertai ministerial controls: do not mislabel their original 臣 as 奴才.
 for fname,source,needle in [('ertai','https://www.shidianguji.com/zh/book/CADAL02083189/chapter/1lhgyue10hvzi','臣跪誦之下'),('yang','https://www.shidianguji.com/zh/book/SK0845/chapter/1kfb0jjuhbg96','湖廣總督臣楊宗仁')]:
  text=compact((R/'sources'/f'{fname}.txt').read_text());p=text.find(needle)
  if p>=0:
   at=text.index('臣',p);add(text[max(0,at-1000):at],'臣',kind='documentary_control',group='original_chen',source=source,doc_id=fname)
 nian=compact((R/'sources/nian_museum.txt').read_text());needle='四川巡撫、加三級臣年羹堯謹奏';at=nian.find(needle)
 if at>=0:add(nian[at:at+needle.index('臣')],'臣',kind='documentary_control',group='original_chen',source='https://www.npm.gov.tw/NewChineseArtDownload.ashx?bid=4770',doc_id='Nian_original_chen')
 # Word tokenization printed before model load, including modern calibration anchors.
 cuts={}
 for p in probes:cuts[p['target']]=dict(target=p['target'],ids=p['target_ids'],tokens=p['target_tokens'],decoded=[tok.decode([i]) for i in p['target_ids']])
 for row in cuts.values():print('TOKEN',json.dumps(row,ensure_ascii=False),flush=True)
 save('tokenization.json',list(cuts.values()));save('probes.json',probes);save('pairs.json',pairs);save('samples.json',samples);save('source_slice_verification.json',verification)
 save('design.json',dict(n_probes=len(probes),n_pairs=len(pairs),n_samples=len(samples),heavy_directory=str(HEAVY),english_intro_words=len(INTRO.split()),target_counts={g:sum(x['group']==g and x['target']=='奴才' and x['wrapper']=='W2_native' for x in samples) for g in sorted({x['group'] for x in samples})},wrapper_tokens={w:len(tok.encode(p,add_special_tokens=False)) for w,p in wraps.items()},causal_policy='Every probe ends at target; all wrapped text precedes target; right context saved for audit only, never forwarded; no BOS/templates',sha256=hashlib.sha256((R/'probes.json').read_bytes()).hexdigest()))
 print('PREPARED',len(probes),'unique probes',sum(p['token_count'] for p in probes),'forward tokens',flush=True)
if __name__=='__main__':build()
