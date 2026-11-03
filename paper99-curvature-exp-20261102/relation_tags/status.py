from pathlib import Path
import json,time
root=Path('/home/lmxxf/work/interp-curvature-exp/relation_tags')
print(json.dumps(dict(time=time.strftime('%F %T'),cases={d.name:len(list(d.glob('rel_*.json'))) for d in (root/'raw').iterdir()},expected_per_model=126),ensure_ascii=False))
