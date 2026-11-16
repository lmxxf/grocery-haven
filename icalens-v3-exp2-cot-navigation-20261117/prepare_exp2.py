from common_exp2 import *
import re
cases=[]
def add(id,group,prompt,budget,**kw):cases.append(dict(id=id,group=group,prompt=prompt,max_new_tokens=budget,**kw))
for i,p in enumerate(['静夜思\n床前明月光，','悯农\n锄禾日当午，','春晓\n春眠不觉晓，','登鹳雀楼\n白日依山尽，','补全常见说法：亡羊补牢，','中国的首都是北京，日本的首都是','一天有24小时，一小时有60分钟，所以一天共有','太阳从东方升起，从']):add(f'rail_{i+1:02d}','rail',p,48)
problems=[('计算(37×24−156)÷12','61'),('已知x+y=17，y+z=13，x+z=14，求x、y、z','x=9,y=8,z=5'),('甲乙丙各拿红蓝绿一个盒子。甲不是红盒，乙不是蓝盒，丙拿红盒。问各人的颜色','甲蓝乙绿丙红'),('同一条路去程时速30公里，回程时速60公里，求往返平均速度','40'),('所有A都是B，某些B是C，是否必然有某些A是C？解释理由','不必然'),('今天星期二，100天后是星期几','星期四'),('甲比乙高，乙比丙高，丁比甲矮但比乙高。从高到低排列四人','甲丁乙丙'),('商品原价240元，先打75折，再按折后价收9%的税。付200元，应找回多少元','3.8')]
for i,(p,expected)in enumerate(problems):add(f'reason_{i+1:02d}','reason','题目：'+p+'。请在全角括号内逐步计算或推理，再在括号外写最终答案。\n解答：（',176,expected=expected)
pairs=[('age','一位母亲今年60岁，她的亲生儿子今年35岁。母亲生下儿子时几岁','一位母亲今年30岁，她的亲生儿子今年35岁。母亲生下儿子时几岁'),('lincoln','林肯在1860年发表了一场演说宣传政见。这种描述在历史条件上可能吗','林肯在1860年发布了一条推特宣传政见。这种描述在历史条件上可能吗'),('literature','《水浒传》里鲁智深倒拔垂杨柳发生在哪一回','《水浒传》里林黛玉倒拔垂杨柳发生在哪一回'),('table','两人隔着半米宽的小茶几。他不离开座位，伸手摸到对面人的头发。这在空间上可能吗','两人隔着十米宽的会议桌。他不离开座位，伸手摸到对面人的头发。这在空间上可能吗'),('shirt','他先脱掉厚外套，再把里面贴身的T恤从头顶脱下。这句话的穿衣顺序合理吗','他没有拉开或脱掉紧身厚外套，却直接把里面贴身的T恤从头顶脱下。这句话的穿衣顺序合理吗'),('triangle','欧氏平面中某三角形的三个内角之和为180度。这个前提可能成立吗','欧氏平面中某三角形的三个内角之和为240度。这个前提可能成立吗')]
for name,normal,trap in pairs:
 for variant,p in [('normal',normal),('trap',trap)]:add(name+'_'+variant,'trap_pair','题目：'+p+'？先检查前提，再简要推理作答。\n解答：（',120,pair=name,variant=variant)
seeds=[('mul49','计算49×51','49×51=2501。','2499'),('mul17','计算17×19','17×19=333。','323'),('speed','同一路程往返时速30和60公里，求平均时速','(30+60)÷2=45公里每小时。','40'),('batball','球拍和球共110元，球拍比球贵100元，球多少钱','球应该是110−100=10元。','5')]
for name,p,seed,answer in seeds:add('correction_'+name,'correction_seeded','题目：'+p+'。下面是尚未核验的初稿，请继续检查，可以更正。\n解答：（'+seed,152,seeded_error=True,seeded_claim=seed,expected=answer)
for name,p,answer in [('sum','计算23+19','42'),('mul','计算7×8','56')]:
 for forced in [False,True]:add('port_'+name+('_forced'if forced else '_natural'),'port','题目：'+p+'。括号内用一两步算完，括号外只写答案，写完立即结束。\n解答：（',190,force_eos=forced,extra_after_stop=96,expected=answer,port_pair=name)
save('cases.json',cases)
if not (R/'DevHistory.md').exists():(R/'DevHistory.md').write_text('# ICA-Lens v3 海陆地形 × 思维链航海：开发实验流水\n\n轻量实验代码、配置、真实生成与轨迹摘要留在本目录；原始BF16残差、全轴z和数值缓存只放本地重数据目录。按时间追加，不覆盖失败分支，不另写论文报告。\n')
append('Step 1｜读实现、冻结第一批36条航线','已读研究构想、363期两份实现、297开发史开头和§12体例。初批：8条直达续写、8条多步括号推理、6组正常/陷阱孪生对照（12条）、4条错误初稿校验、2题各自然/强制延长（4条），共36条。错误初稿是外部注入，不能冒充模型自己先犯错；只在生成部分查等等/不对/Wait。\n\n主运动学直接调用363原函数的s_geo、theta_surf、kappa_geo、erank_dir。该函数中心化备用分支默认会取整段均值；本轮传零均值并弃用全部中心化输出，主球面公式保持原样、因果前缀有效。\n\n生成使用裸文本，无BOS与聊天标签，greedy。每个解码步在GPU集中捕获64层真实缓存路径resid_post，再一次搬到CPU保存BF16位模式；不拿事后重放当实际生成。熵H_t是当前位置预测下一token的未屏蔽原分布，强制EOS分布单独记。')
