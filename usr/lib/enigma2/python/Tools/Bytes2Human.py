def bytes2human(number, digits=2):
	symbols = ("KB", "MB", "GB", "TB", "PB")
	prefix = {}
	for idx, symbol in enumerate(symbols):
		prefix[symbol] = 1 << (idx + 1) * 10
	for s in reversed(symbols):
		if number >= prefix[s]:
			value = round(float(number) / prefix[s], digits) if digits > 0 else number / prefix[s]
			return f"{value} {s}"
	return f"{number} B"
