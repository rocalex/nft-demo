# Trade Contract

Trade contract has following 3 methods: 

[on_create()](#on_create)

[on_setup()](#on_setup)

[on_replace()](#on_replace)


## on_create()
Creating application

While creating application, initializing asset count on global state.
After create application, the app creator should charge min balance and setup fee (0.203 Algo) of application


## on_setup()
Opt app into providing assets(base, silver, gold, diamond)

### Single transaction: 
[App call transaction]

* Application call transaction
  * Assets: [base, silver, gold, diamond]

### Inner transaction: 
4 inner transactions to opt app into asset


## on_replace()
Revoke base asset and sender higher asset.

### Single transaction: 

[App call transaction]

* Application call transaction
  * App args: Amount of 
  * Assets: [base_asset_id, higher_asset_id]

