def bytes2human(n, digits=2):
	symbols = ('KB', 'MB', 'GB', 'TB', 'PB')
	prefix = {}
	for i, s in enumerate(symbols):
		prefix[s] = 1 << (i + 1) * 10
	for s in reversed(symbols):
		if n >= prefix[s]:
			value = round(float(n) / prefix[s], digits) if digits > 0 else n / prefix[s]
			return f"{value} {s}"
	return f"{n} B"
