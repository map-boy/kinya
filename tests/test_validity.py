from kinya import validity as v
def D(turns, sector="Kimironko"):
    return {"turns": [{"role": r, "text": t} for r, t in turns], "route": {"sector": sector}}
GOOD = D([("caller","Muraho, amazi yacitse mu Kimironko."),("agent","Muraho neza, mbwira neza aho uri."),
          ("caller","Ndi mu Kimironko hafi y'isoko."),("agent","Murakoze, ikibazo cyanyu cyanditswe kandi cyoherejwe muri WASAC.")])
def test_good(): assert v.check(GOOD, None, ["Kimironko"]) == (True, "")
def test_agent_first():
    assert v.check(D([("agent","Muraho"+"x"*3),("caller","Muraho Kimironko"),("agent","Ni ibihe?"),("caller","Amazi")]))[1] == "bad_turn_order"
def test_promise():
    d = D([("caller","Muraho, Kimironko."),("agent","Muraho neza."),("caller","Amazi yacitse."),("agent","Tuzaza mu minota 5.")])
    assert v.check(d)[1] == "agent_number_promise"
def test_sector_unknown(): assert v.check(GOOD, None, ["Remera"])[1] == "unknown_sector"
def test_sector_missing():
    d = D([("caller","Muraho, amazi yacitse."),("agent","Muraho neza."),("caller","Ni hano iwacu."),("agent","Murakoze cyane.")])
    assert v.check(d)[1] == "sector_not_in_text"
def test_english():
    d = D([("caller","Hello please thank you Kimironko"),("agent","Muraho neza."),("caller","Amazi yacitse."),("agent","Murakoze cyane.")])
    assert v.check(d)[1] == "english_leak"
def test_loop():
    t = "nk'ubwozi bwo nk'ubwozi bwo nk'ubwozi bwo nk'ubwozi Kimironko"
    d = D([("caller",t),("agent","Muraho neza."),("caller","Amazi yacitse."),("agent","Murakoze cyane.")])
    assert v.check(d)[1] == "repetition"
def test_consecutive(): 
    d = D([("caller","Muraho Kimironko."),("caller","Amazi yacitse."),("agent","Muraho neza."),("agent","Murakoze cyane.")])
    assert v.check(d)[1] == "bad_turn_order"