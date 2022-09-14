import smartpy as sp

class Contract(sp.Contract):
  def __init__(self):
    self.init_type(sp.TRecord(administrator = sp.TAddress, creator = sp.TAddress, fa2 = sp.TAddress, ledger = sp.TBigMap(sp.TNat, sp.TAddress), metadata = sp.TBigMap(sp.TString, sp.TBytes), next_token_id = sp.TNat, operators = sp.TBigMap(sp.TRecord(operator = sp.TAddress, owner = sp.TAddress, token_id = sp.TNat).layout(("owner", ("operator", "token_id"))), sp.TUnit), paused = sp.TBool, proposed_administrator = sp.TOption(sp.TAddress), token_metadata = sp.TBigMap(sp.TNat, sp.TRecord(token_id = sp.TNat, token_info = sp.TMap(sp.TString, sp.TBytes)).layout(("token_id", "token_info")))).layout(((("administrator", "creator"), ("fa2", ("ledger", "metadata"))), (("next_token_id", "operators"), ("paused", ("proposed_administrator", "token_metadata"))))))
    self.init(administrator = sp.address('tz1hdQscorfqMzFqYxnrApuS5i6QSTuoAp3w'),
              creator = sp.address('tz1hdQscorfqMzFqYxnrApuS5i6QSTuoAp3w'),
              fa2 = sp.address('tz1KozzwY6LrGDsZkTPLGwbh13HNezL21JMV'),
              ledger = {},
              metadata = {'' : sp.bytes('0x68747470733a2f2f6578616d706c652e636f6d')},
              next_token_id = 0,
              operators = {},
              paused = False,
              proposed_administrator = sp.none,
              token_metadata = {})

  @sp.entry_point
  def accept_administrator(self):
    sp.verify(self.data.proposed_administrator.is_some(), 'MINTER_NO_NEW_ADMIN')
    sp.verify(sp.sender == self.data.proposed_administrator.open_some(), 'MINTER_NOT_PROPOSED_ADMIN')
    self.data.administrator = sp.sender
    self.data.proposed_administrator = sp.none

  @sp.entry_point
  def accept_fa2_administrator(self):
    sp.verify(sp.sender == self.data.administrator, 'MINTER_NOT_ADMIN')
    sp.send(self.data.fa2, sp.tez(0))

  @sp.entry_point
  def balance_of(self, params):
    sp.set_type(params, sp.TRecord(callback = sp.TContract(sp.TList(sp.TRecord(balance = sp.TNat, request = sp.TRecord(owner = sp.TAddress, token_id = sp.TNat).layout(("owner", "token_id"))).layout(("request", "balance")))), requests = sp.TList(sp.TRecord(owner = sp.TAddress, token_id = sp.TNat).layout(("owner", "token_id")))).layout(("requests", "callback")))
    def f_x0(_x0):
      sp.verify(_x0.token_id < self.data.next_token_id, 'FA2_TOKEN_UNDEFINED')
      sp.result(sp.record(request = sp.record(owner = _x0.owner, token_id = _x0.token_id), balance = sp.eif(self.data.ledger[_x0.token_id] == _x0.owner, 1, 0)))
    sp.transfer(params.requests.map(sp.build_lambda(f_x0)), sp.tez(0), params.callback)

  @sp.entry_point
  def mint(self, params):
    sp.verify(~ self.data.paused, 'MINT_PAUSED')
    sp.verify(sp.sender == self.data.administrator, 'FA2_NOT_ADMIN')
    compute_NFT_171i = sp.local("compute_NFT_171i", self.data.next_token_id)
    self.data.token_metadata[compute_NFT_171i.value] = sp.record(token_id = compute_NFT_171i.value, token_info = params.metadata)
    self.data.ledger[compute_NFT_171i.value] = params.to_
    self.data.next_token_id += 1

  @sp.entry_point
  def set_pause(self, params):
    sp.set_type(params, sp.TBool)
    sp.verify(sp.sender == self.data.administrator, 'MINTER_NOT_ADMIN')
    self.data.paused = params

  @sp.entry_point
  def transfer(self, params):
    sp.for transfer in params:
      sp.for tx in transfer.txs:
        sp.set_type(tx, sp.TRecord(amount = sp.TNat, to_ = sp.TAddress, token_id = sp.TNat).layout(("to_", ("token_id", "amount"))))
        sp.verify(tx.token_id < self.data.next_token_id, 'FA2_TOKEN_UNDEFINED')
        sp.verify((transfer.from_ == sp.sender) | (self.data.operators.contains(sp.record(owner = transfer.from_, operator = sp.sender, token_id = tx.token_id))), 'FA2_NOT_OPERATOR')
        sp.if tx.amount > 0:
          sp.verify((tx.amount == 1) & (self.data.ledger[tx.token_id] == transfer.from_), 'FA2_INSUFFICIENT_BALANCE')
          self.data.ledger[tx.token_id] = tx.to_

  @sp.entry_point
  def transfer_administrator(self, params):
    sp.set_type(params, sp.TAddress)
    sp.verify(sp.sender == self.data.administrator, 'MINTER_NOT_ADMIN')
    self.data.proposed_administrator = sp.some(params)

  @sp.entry_point
  def transfer_fa2_administrator(self, params):
    sp.set_type(params, sp.TAddress)
    sp.verify(sp.sender == self.data.administrator, 'MINTER_NOT_ADMIN')
    sp.transfer(params, sp.tez(0), sp.contract(sp.TAddress, self.data.fa2, entry_point='transfer_administrator').open_some())

  @sp.entry_point
  def update_operators(self, params):
    sp.for update in params:
      with update.match_cases() as arg:
        with arg.match('add_operator') as add_operator:
          sp.verify(add_operator.owner == sp.sender, 'FA2_NOT_OWNER')
          self.data.operators[add_operator] = sp.unit
        with arg.match('remove_operator') as remove_operator:
          sp.verify(remove_operator.owner == sp.sender, 'FA2_NOT_OWNER')
          del self.data.operators[remove_operator]


sp.add_compilation_target("test", Contract())