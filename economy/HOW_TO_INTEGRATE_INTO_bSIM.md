# HOW TO INTEGRATE THE ECONOMY INTO bSIM (Very Simple Guide)

This guide is written for people who are not Python experts.

## Step 1: Put the economy folder in the right place

You should have a folder called `economy/` that contains:
- `asset.py`
- `bSIM_economy_bridge.py`
- `pedersen.py`
- `save_format.py`
- `templates.py`
- `svc_coin.py`
- `__init__.py`
- `bSIM_integration_guide.py`   ← This is the important one for you right now

Put the whole `economy/` folder somewhere bSIM can import from (same folder as your main game files is easiest).

## Step 2: Use the simple guide file

The file `bSIM_integration_guide.py` was made to be as easy as possible.

### What you should do:

1. Open `bSIM_integration_guide.py`
2. At the very top of your main game file (or any file where you handle loot, items, saving, etc.), add this line:

```python
from bSIM_integration_guide import (
    on_loot_drop,
    on_consume_item,
    on_player_trade,
    save_player_game,
    load_player_game
)
```

3. Then use the functions when these things happen in your game.

## Step 3: Where to call the functions (Copy & Paste Examples)

### A. When a player gets loot (most common)

Find the place in your code where loot is given to the player.

Add this:

```python
on_loot_drop(
    player_id = player.id,                    # the player's ID
    asset_id = "cool_sword_01",               # unique name for this item
    pah_path = "/pqc_assets/loot/cool_sword.pqcasset"   # path to the wrapped file
)
```

### B. When a player uses/consumes an item

Find where items are used.

Add this:

```python
on_consume_item(
    player_id = player.id,
    asset_id = item.asset_id
)
```

### C. When saving the game

Find where you save player progress (logout, checkpoint, etc.).

Add this:

```python
save_player_game(player_id = player.id)
```

### D. When loading a player (login)

Find where players log in or load their character.

Add this:

```python
load_player_game(player_id = player.id)
```

## Step 4: Test it

After adding the calls above, run your game and do these actions:
1. Get some loot
2. Use an item
3. Save and reload

The economy system should now track the player's items.

---

You don't need to understand how everything works inside the `economy/` folder.
Just use the 5 functions from `bSIM_integration_guide.py`.

If you get any errors, copy the error message and send it here.
