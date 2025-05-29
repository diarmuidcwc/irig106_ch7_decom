import pstats

ps = pstats.Stats("output.data")
ps.sort_stats(pstats.SortKey.CUMULATIVE).print_stats(30)
print("------------------")
ps.sort_stats(pstats.SortKey.TIME).print_stats(30)
