import os
import chess.pgn
import numpy as np

from state import State

def get_dataset(num_samples = None):
#pgn files downloaded
    X,Y = [], []
    values = {'1/2-1/2': 0, '0-1':-1, '1-0':1}
    gn = 0
    for fn in os.listdir("data"):
        pgn= open(os.path.join("data", fn))
        while 1:
            try:
                game = chess.pgn.read_game(pgn)
            except Exception:
                break
            res = game.headers['Result']
            if res not in values:
                continue
            value = values[res]
            board = game.board()
            for i, move in enumerate(game.mainline_moves()):
                board.push(move)
                ser =  State(board).serialize()
                X.append(ser)
                Y.append(value)
            print("Parsing game %d, got %d examples" % (gn, len(X)))
            if num_samples is not None and len(X) > num_samples:
                return X,Y
            gn += 1
    X = np.array(X)
    Y = np.array(Y)
    return X, Y


import h5py

if __name__ == "__main__":
    X,Y = get_dataset(5000000)
    np.savez("processed/dataset_5mil.npz", X, Y)