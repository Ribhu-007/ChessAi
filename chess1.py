import traceback
import base64
import torch
import time
from state import State
from train import Net
import chess
import chess.svg
import os


class Valuator(object):
    def __init__(self):
        vals = torch.load("nets/value.pth", map_location=lambda storage, loc: storage)
        self.model = Net()
        self.model.load_state_dict(vals)

    def __call__(self, s):
        brd = s.serialize()[None]
        output = self.model(torch.tensor(brd).float())
        return float(output.data[0][0])

#writing a simple chess value function
MAXVAL = 10000
class ClassicValuator(object):
  values = {chess.PAWN: 1,
            chess.KNIGHT: 3,
            chess.BISHOP: 3,
            chess.ROOK: 5,
            chess.QUEEN: 9,
            chess.KING: 0}

  def __init__(self):
    self.reset()
    self.memo = {}

  def reset(self):
      self.count = 0


  # writing a simple value function based on pieces
  def __call__(self, s):
    self.count+= 1
    key = s.key()
    if key not in self.memo:
        self.memo[key] = self.value(s)
    return self.memo[key]

  def value(self,s):
    b = s.board
    if b.is_variant_win():
      if b.turn == chess.WHITE:
        return MAXVAL
      else:
        return -MAXVAL
    if b.is_variant_loss():
      if b.turn == chess.WHITE:
        return -MAXVAL
      else:
        return MAXVAL
    val = 0.0
    pm = s.board.piece_map()
    for x in pm:
      tval = self.values[pm[x].piece_type]
      if pm[x].color == chess.WHITE:
        val += tval
      else:
        val -= tval
    bak = b.turn
    b.turn = chess.WHITE
    val += 0.1 * b.legal_moves.count()
    b.turn = chess.BLACK
    val -= 0.1 * b.legal_moves.count()
    b.turn = bak
    return val


def computer_minimax(s, v, depth=2):
  if depth == 0 or s.board.is_game_over():
    return v(s)
  # white is maximizing player
  turn = s.board.turn
  if turn == chess.WHITE:
    ret = -MAXVAL
  else:
    ret = MAXVAL
  for e in s.edges():
    s.board.push(e)
    tval = computer_minimax(s, v, depth-1)
    if turn == chess.WHITE:
      ret = max(ret, tval)
    else:
      ret = min(ret, tval)
    s.board.pop()
  return ret

def explore_leaves(s,v):
    ret =[]
    start = time.monotonic()
    v.reset()
    for e in s.edges():
        s.board.push(e)
        #ret.append((v(s), e))
        ret.append((computer_minimax(s,v),e))
        s.board.pop()
    eta = time.monotonic() - start
    print("explored %d nodes in %.3f seconds" % (v.count, eta))
        #for each move evaluations how likely you are to win
    return ret

#def minimax(node, depth, maximizingPlayer)



#Chess board and engine
s = State()
#v = Valuator()
v = ClassicValuator()

def to_svg(s):
    return base64.b64encode(chess.svg.board(board=s.board).encode('utf-8')).decode('utf-8')


from flask import Flask, Response, request
app = Flask(__name__)

@app.route("/")
def hello():
    ret = open("index.html").read()
    return ret.replace('start', s.board.fen())
# @app.route("/board.svg")
# def board():
#     return Response(chess.svg.board(board=s.board), mimetype='image/svg+xml')


def computer_move(s,v):
    # computer move
    move = sorted(explore_leaves(s, v), key=lambda x: x[0], reverse=s.board.turn)
    if len(move) == 0:
        return
    print("top 3:")
    for i, m in enumerate(move[0:3]):
        print("  ", m)
    print(s.board.turn,"moving", move[0][1])
    s.board.push(move[0][1])



@app.route("/selfplay")
def selfplay():
    s = State()

    ret = '<html><head>'

    while not s.board.is_game_over():
        computer_move(s,v)
        ret += '<img width=800 height=800 src ="data:image/svg+xml;base64,%s"></img><br/>' % to_svg(s)
    print(s.board.result())
    return ret

@app.route("/move")
def move():
    if not s.board.is_game_over():
        move = request.args.get('move', default="")
        if move is not None and move != "":
            print("human moves", move)
            try:
                s.board.push_san(move)
                computer_move(s, v)
            except Exception:
                traceback.print_exc()
            response = app.response_class(
                response=s.board.fen(),
                status=200
            )
            return response
    else:
        print("GAME IS OVER")
        response = app.response_class(
            response="game over",
            status=200
        )
        return response
    print("hello ran")
    return hello()

# moves given as coordinates of piece moved
@app.route("/move_coordinates")
def move_coordinates():
  if not s.board.is_game_over():
    source = int(request.args.get('from', default=''))
    target = int(request.args.get('to', default=''))
    promotion = True if request.args.get('promotion', default='') == 'true' else False

    move = s.board.san(chess.Move(source, target, promotion=chess.QUEEN if promotion else None))

    if move is not None and move != "":
      print("human moves", move)
      try:
        s.board.push_san(move)
        computer_move(s, v)
      except Exception:
        traceback.print_exc()
    response = app.response_class(
      response=s.board.fen(),
      status=200
    )
    return response

  print("GAME IS OVER")
  response = app.response_class(
    response="game over",
    status=200
  )
  return response

@app.route("/newgame")
def newgame():
  s.board.reset()
  response = app.response_class(
    response=s.board.fen(),
    status=200
  )
  return response

if __name__ == "__main__":
    if os.getenv("SELFPLAY") is not None:
        s = State()
        while not s.board.is_game_over():
            computer_move(s, v)
            print(s.board)
        print(s.board.result())
    else:
        app.run(debug=True)



'''if __name__ == "__main__": 
    #self play
    while not s.board.is_game_over():
        l = sorted(explore_leaves( s,v), key = lambda x:x[0], reverse=s.board.turn)
        move = l[0]
        print(move)
        s.board.push(move[1])
    print(s.board.result()'''

