from kipy import KiCad

kicad = KiCad()
print(kicad.get_version())
board = kicad.get_board()
print(f"{len(board.get_footprints())} empreintes, {len(board.get_tracks())} pistes")