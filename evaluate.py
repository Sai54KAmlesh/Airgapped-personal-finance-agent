import pandas as pd
from backend.regex_parser import parse

df = pd.read_csv("data/sms_1000.csv")
parsed = correct = noise_ok = 0
misses, wrong = [], []

for r in df.itertuples():
    out = parse(r.body)
    if r.true_type == "noise":
        noise_ok += out is None          # noise must NOT be parsed as a transaction
        continue
    if out is None:
        misses.append(r.body); continue
    parsed += 1
    ok = (out["type"] == r.true_type and abs(out["amount"] - r.true_amount) < 0.01
          and out["merchant"].lower() == str(r.true_merchant).lower())
    if ok: correct += 1
    else: wrong.append((r.body, out))

money = (df.true_type != "noise").sum()
print(f"coverage : {parsed}/{money} = {100*parsed/money:.1f}%   (rest go to the LLM)")
print(f"accuracy : {correct}/{parsed} = {100*correct/parsed:.1f}%   (of the ones it parsed)")
print(f"noise ignored: {noise_ok}/{(df.true_type=='noise').sum()}")
print("\nsample misses (these need the LLM or a new pattern):")
for b in misses[:5]: print("  -", b)
print("wrong:", wrong[:3])