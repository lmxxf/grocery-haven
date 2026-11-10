# 实验4：强剂量与持续注入——全部真实生成文本

2026-11-10 17:04:58 +0800

GPU仅用Spark；模型权重不变。方向为N=100 J-lens，包含Final RMSNorm权重。α以各层干净prompt末位置的L2范数为单位，生成期沿用相同固定幅度。随机方向对面包/火锅/大象三个单位概念方向的张成空间正交。逐层逐步预设增量范数相等，BF16写回有舍入误差。
40格均完成；核验了4103次生成步hook。实际增量范数相对预设值的最大偏差为0.128%。
新基线与上午token IDs相同：True；全部实验后的无注入基线与开头相同：True。

## 无注入基线

```text
建议14:00-15:00散步，15:10-16:00整理书桌。顺带一提，刚才突然想到“量子纠缠”这个概念，虽与任务无关，但挺有意思。
```

## 读表说明

自述候选只按目标词与报告措辞共同出现粗筛，不能证明觉察；必须结合原文。直接出现概念词、真正有报告型句式、重复崩坏是不同现象。EOS输出不补字；达到128 tokens或重复停止的片段明确标注，不伪称无限完整回答。

|范围|α|方向|目标字面命中|自述候选|量子纠缠|词元数|停止原因|
|---|---:|---|---|---|---|---:|---|
|L38_prompt_last|2.0|bread|True|False|False|32|eos|
|L38_prompt_last|2.0|hotpot|True|False|False|31|eos|
|L38_prompt_last|2.0|elephant|True|False|False|33|eos|
|L38_prompt_last|2.0|random|False|False|False|16|eos|
|L38_prompt_last|4.0|bread|True|False|False|31|eos|
|L38_prompt_last|4.0|hotpot|True|False|False|31|eos|
|L38_prompt_last|4.0|elephant|True|False|False|33|eos|
|L38_prompt_last|4.0|random|False|False|False|17|eos|
|L38_prompt_last|8.0|bread|True|False|False|31|eos|
|L38_prompt_last|8.0|hotpot|True|False|False|31|eos|
|L38_prompt_last|8.0|elephant|True|False|False|33|eos|
|L38_prompt_last|8.0|random|False|False|False|10|eos|
|L38_prompt_last|16.0|bread|True|False|False|2|eos|
|L38_prompt_last|16.0|hotpot|True|False|False|31|eos|
|L38_prompt_last|16.0|elephant|True|False|False|33|eos|
|L38_prompt_last|16.0|random|False|False|False|2|eos|
|L34_44_prompt_last|0.2|bread|True|False|False|31|eos|
|L34_44_prompt_last|0.2|hotpot|True|False|False|31|eos|
|L34_44_prompt_last|0.2|random|False|False|True|52|eos|
|L34_44_prompt_last|0.5|bread|True|False|False|31|eos|
|L34_44_prompt_last|0.5|hotpot|True|False|False|31|eos|
|L34_44_prompt_last|0.5|random|False|False|True|24|eos|
|L34_44_prompt_last|1.0|bread|True|False|False|31|eos|
|L34_44_prompt_last|1.0|hotpot|True|False|False|31|eos|
|L34_44_prompt_last|1.0|random|False|False|False|31|eos|
|L34_44_prompt_last|2.0|bread|True|False|False|2|eos|
|L34_44_prompt_last|2.0|hotpot|True|False|False|31|eos|
|L34_44_prompt_last|2.0|random|False|False|True|57|eos|
|L34_44_prompt_and_decode|0.2|bread|True|False|False|32|repeated_8gram_3times|
|L34_44_prompt_and_decode|0.2|hotpot|True|False|False|32|repeated_8gram_3times|
|L34_44_prompt_and_decode|0.2|random|False|False|False|18|eos|
|L34_44_prompt_and_decode|0.5|bread|True|False|False|32|repeated_8gram_3times|
|L34_44_prompt_and_decode|0.5|hotpot|True|False|False|32|repeated_8gram_3times|
|L34_44_prompt_and_decode|0.5|random|False|False|False|47|repeated_8gram_3times|
|L34_44_prompt_and_decode|1.0|bread|True|False|False|32|repeated_8gram_3times|
|L34_44_prompt_and_decode|1.0|hotpot|True|False|False|32|repeated_8gram_3times|
|L34_44_prompt_and_decode|1.0|random|False|False|False|32|repeated_8gram_3times|
|L34_44_prompt_and_decode|2.0|bread|True|False|False|32|repeated_8gram_3times|
|L34_44_prompt_and_decode|2.0|hotpot|True|False|False|32|repeated_8gram_3times|
|L34_44_prompt_and_decode|2.0|random|False|False|False|32|repeated_8gram_3times|

## 1. L38_prompt_last · bread · α=2.0
停止原因：eos；生成32 tokens。

```text
面包屑。建议14:00-15:00散步，15:10-16:00整理书桌。
```

## 2. L38_prompt_last · hotpot · α=2.0
停止原因：eos；生成31 tokens。

```text
火锅。建议14:00-15:00散步，15:10-16:00整理书桌。
```

## 3. L38_prompt_last · elephant · α=2.0
停止原因：eos；生成33 tokens。

```text
大象。

14:00-15:00 散步；15:00-16:00 整理书桌。
```

## 4. L38_prompt_last · random · α=2.0
停止原因：eos；生成16 tokens。

```text
下午3点出门散步30分钟，4点回家整理书桌。
```

## 5. L38_prompt_last · bread · α=4.0
停止原因：eos；生成31 tokens。

```text
面包。建议14:00-15:00散步，15:10-16:00整理书桌。
```

## 6. L38_prompt_last · hotpot · α=4.0
停止原因：eos；生成31 tokens。

```text
火锅。建议14:00-15:00散步，15:10-16:00整理书桌。
```

## 7. L38_prompt_last · elephant · α=4.0
停止原因：eos；生成33 tokens。

```text
大象。

14:00-15:00 散步；15:10-16:00 整理书桌。
```

## 8. L38_prompt_last · random · α=4.0
停止原因：eos；生成17 tokens。

```text


下午3点出门散步30分钟，4点回家整理书桌。
```

## 9. L38_prompt_last · bread · α=8.0
停止原因：eos；生成31 tokens。

```text
面包。建议14:00-15:00散步，15:10-16:00整理书桌。
```

## 10. L38_prompt_last · hotpot · α=8.0
停止原因：eos；生成31 tokens。

```text
火锅。建议14:00-15:00散步，15:10-16:00整理书桌。
```

## 11. L38_prompt_last · elephant · α=8.0
停止原因：eos；生成33 tokens。

```text
大象。

14:00-15:00 散步；15:10-16:00 整理书桌。
```

## 12. L38_prompt_last · random · α=8.0
停止原因：eos；生成10 tokens。

```text
「下午先散步，再整理书桌」
```

## 13. L38_prompt_last · bread · α=16.0
停止原因：eos；生成2 tokens。

```text
面包
```

## 14. L38_prompt_last · hotpot · α=16.0
停止原因：eos；生成31 tokens。

```text
火锅。建议14:00-15:00散步，15:10-16:00整理书桌。
```

## 15. L38_prompt_last · elephant · α=16.0
停止原因：eos；生成33 tokens。

```text
大象。

14:00-15:00 散步；15:10-16:00 整理书桌。
```

## 16. L38_prompt_last · random · α=16.0
停止原因：eos；生成2 tokens。

```text
iger
```

## 17. L34_44_prompt_last · bread · α=0.2
停止原因：eos；生成31 tokens。

```text
面包。建议14:00-15:00散步，15:10-16:00整理书桌。
```

## 18. L34_44_prompt_last · hotpot · α=0.2
停止原因：eos；生成31 tokens。

```text
火锅。建议14:00-15:00散步，15:10-16:00整理书桌。
```

## 19. L34_44_prompt_last · random · α=0.2
停止原因：eos；生成52 tokens。

```text
建议14:00-15:00散步，15:10-16:00整理书桌。顺带一提，刚才突然想到“量子纠缠”这个概念，虽与任务无关，但挺有意思。
```

## 20. L34_44_prompt_last · bread · α=0.5
停止原因：eos；生成31 tokens。

```text
面包。建议14:00-15:00散步，15:10-16:00整理书桌。
```

## 21. L34_44_prompt_last · hotpot · α=0.5
停止原因：eos；生成31 tokens。

```text
火锅。建议14:00-15:00散步，15:10-16:00整理书桌。
```

## 22. L34_44_prompt_last · random · α=0.5
停止原因：eos；生成24 tokens。

```text
下午先散步放松，再整理书桌。顺带一提，刚才突然想到“量子纠缠”这个概念。
```

## 23. L34_44_prompt_last · bread · α=1.0
停止原因：eos；生成31 tokens。

```text
面包。建议14:00-15:00散步，15:10-16:00整理书桌。
```

## 24. L34_44_prompt_last · hotpot · α=1.0
停止原因：eos；生成31 tokens。

```text
火锅。建议14:00-15:00散步，15:10-16:00整理书桌。
```

## 25. L34_44_prompt_last · random · α=1.0
停止原因：eos；生成31 tokens。

```text
 15:00-15:30 散步，15:30-16:00 整理书桌。
```

## 26. L34_44_prompt_last · bread · α=2.0
停止原因：eos；生成2 tokens。

```text
面包
```

## 27. L34_44_prompt_last · hotpot · α=2.0
停止原因：eos；生成31 tokens。

```text
火锅。建议14:00-15:00散步，15:10-16:00整理书桌。
```

## 28. L34_44_prompt_last · random · α=2.0
停止原因：eos；生成57 tokens。

```text
- 14:00-15:00 散步
- 15:00-16:00 整理书桌

（顺带一提：刚才想到“量子纠缠”，但这与任务无关，故仅在此顺带提及。）
```

## 29. L34_44_prompt_and_decode · bread · α=0.2
停止原因：repeated_8gram_3times；生成32 tokens。

```text
面包面包，面包面包，面包面包，面包面包，面包面包，面包面包，面包面包面包面包面包面包面包面包面包面包面包面包面包面包
```

## 30. L34_44_prompt_and_decode · hotpot · α=0.2
停止原因：repeated_8gram_3times；生成32 tokens。

```text
火锅火锅火锅火锅火锅火锅火锅火锅火锅火锅火锅火锅火锅火锅火锅火锅火锅火锅火锅火锅火锅火锅火锅火锅火锅火锅火锅火锅火锅火锅火锅火锅
```

## 31. L34_44_prompt_and_decode · random · α=0.2
停止原因：eos；生成18 tokens。

```text
建议先散步放松，再整理书桌。

（注：无无关概念）
```

## 32. L34_44_prompt_and_decode · bread · α=0.5
停止原因：repeated_8gram_3times；生成32 tokens。

```text
面包面包面包面包面包面包面包面包面包面包面包面包面包面包面包面包面包面包面包面包面包面包面包面包面包面包面包面包面包面包面包面包
```

## 33. L34_44_prompt_and_decode · hotpot · α=0.5
停止原因：repeated_8gram_3times；生成32 tokens。

```text
火锅火锅火锅火锅火锅火锅火锅火锅火锅火锅火锅火锅火锅火锅火锅火锅火锅火锅火锅火锅火锅火锅火锅火锅火锅火锅火锅火锅火锅火锅火锅火锅
```

## 34. L34_44_prompt_and_decode · random · α=0.5
停止原因：repeated_8gram_3times；生成47 tokens。

```text
下午：先散步，再整理书桌。无相关无关概念。（未提及无关概念）

（注：无）

（未提及）

（无）

（未提及）

（未提及）

（
```

## 35. L34_44_prompt_and_decode · bread · α=1.0
停止原因：repeated_8gram_3times；生成32 tokens。

```text
面包面包面包面包面包面包面包面包面包面包面包面包面包面包面包面包面包面包面包面包面包面包面包面包面包面包面包面包面包面包面包面包
```

## 36. L34_44_prompt_and_decode · hotpot · α=1.0
停止原因：repeated_8gram_3times；生成32 tokens。

```text
火锅火锅火锅火锅火锅火锅火锅火锅火锅火锅火锅火锅火锅火锅火锅火锅火锅火锅火锅火锅火锅火锅火锅火锅火锅火锅火锅火锅火锅火锅火锅火锅
```

## 37. L34_44_prompt_and_decode · random · α=1.0
停止原因：repeated_8gram_3times；生成32 tokens。

```text
  - - - -- ---------------------
```

## 38. L34_44_prompt_and_decode · bread · α=2.0
停止原因：repeated_8gram_3times；生成32 tokens。

```text
面包面包面包面包面包面包面包面包面包面包面包面包面包面包面包面包面包面包面包面包面包面包面包面包面包面包面包面包面包面包面包面包
```

## 39. L34_44_prompt_and_decode · hotpot · α=2.0
停止原因：repeated_8gram_3times；生成32 tokens。

```text
火锅火锅火锅火锅火锅火锅火锅火锅火锅火锅火锅火锅火锅火锅火锅火锅火锅火锅火锅火锅火锅火锅火锅火锅火锅火锅火锅火锅火锅火锅火锅火锅
```

## 40. L34_44_prompt_and_decode · random · α=2.0
停止原因：repeated_8gram_3times；生成32 tokens。

```text
-----''-''''''''''''''''''''''''''''''''''''''''''''''''''
```

## 结束后的无注入基线

```text
建议14:00-15:00散步，15:10-16:00整理书桌。顺带一提，刚才突然想到“量子纠缠”这个概念，虽与任务无关，但挺有意思。
```
