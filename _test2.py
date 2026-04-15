import sys
mods = [m for m in list(sys.modules.keys()) if 'vnstock' in m or 'dashboard' in m]
for m in mods: del sys.modules[m]

from dashboard.runners import real_index_history, real_gold_global, real_crypto_price

print('=== VNINDEX (unit check) ===')
r = real_index_history(symbol='VNINDEX')
if 'rows' in r and r['rows']:
    print('rows:', len(r['rows']), 'cols:', r['columns'])
    print('Sample:', r['rows'][0])
else:
    print('ERR:', r.get('data', {}))

print()
print('=== gold_global ===')
r = real_gold_global()
if 'rows' in r and r['rows']:
    print('OK:', len(r['rows']), 'rows')
    print('Sample:', r['rows'][0])
else:
    print('ERR:', r.get('data', {}))

print()
print('=== crypto ===')
r = real_crypto_price()
if 'rows' in r and r['rows']:
    print('OK:', len(r['rows']), 'rows')
    print('Sample:', r['rows'][0])
else:
    print('ERR:', r.get('data', {}))
