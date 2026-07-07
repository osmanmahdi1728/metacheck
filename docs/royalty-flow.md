# Why MetaCheck Exists — How Royalties Flow Across Borders

This is the problem MetaCheck fixes. Independent and African artists lose
royalties not because the money isn't generated, but because their work isn't
*registered and matched correctly* before it goes live. This doc is the
domain reference behind the validator's rules, the CMO check, and the
royalty-at-risk estimator.

## The SACEM → SOCAN → You flow

You never get paid directly by a foreign CMO. Money always flows
**CMO → CMO → you**, and that chain only works if your work is registered at
your home CMO first.

```
Your song plays on French radio
           |
SACEM (France) collects the performance royalty
           |
SACEM checks its database for the rights owner
           |
      Two scenarios:

  REGISTERED (yes)                 NOT REGISTERED (no)
        |                                 |
  SACEM sends to SOCAN            Money sits in a "black box"
        |                                 |
  SOCAN sends to you              Eventually redistributed to OTHER
        |                         rights holders after a holding period
  You get paid                    You get nothing
```

## The full royalty stack most artists miss

When a song streams or plays, multiple royalties are generated
*simultaneously*. Most artists only ever collect one or two of them.

| Royalty type | Who pays | Collected by | Most artists collect? |
|---|---|---|---|
| Streaming performance | Spotify / DSP | Your CMO (e.g. SOCAN) | Sometimes |
| Mechanical (composition) | DSP / Label | MLC (US), CMRRA (CA) | Rarely |
| Radio performance | Broadcaster | SOCAN / SACEM / etc. | Only if registered |
| Sync licensing | Film / TV / Ad | Publisher | Almost never |
| Foreign performance | Foreign broadcaster | Foreign CMO → your CMO | Rarely |
| Neighbouring rights | Radio (for the recording) | Re:Sound (CA), PPL (UK) | Almost never |

**DistroKid collects one of these** — the streaming *master* royalty (what
Spotify pays the distributor, who passes it to you). That's maybe **30–40%**
of what an artist is actually owed.

## Why artists miss the rest

- **No composition registration** — only the recording gets distributed, not
  the underlying song. The composition never gets registered at SOCAN.
- **No publisher** — sync and foreign mechanical royalties require a publisher
  or a publishing admin.
- **No neighbouring-rights registration** — Re:Sound (CA) collects
  neighbouring rights for radio play; almost no indie artists register.
- **ISRC inconsistency** — if the ISRC on Spotify doesn't match what's on file
  at the CMO, they can't match the streams back to the artist.

## The complete setup (what almost nobody does)

| Step | Action | Platform |
|---|---|---|
| 1 | Register as songwriter | SOCAN (free in Canada) |
| 2 | Register every composition | SOCAN work registration |
| 3 | Register as recording artist | Re:Sound (neighbouring rights) |
| 4 | Get publishing admin | Songtrust (~$99/yr) or Sentric |
| 5 | Distribute with ISRC | DistroKid, LANDR, Africori |
| **6** | **Verify ISRC matches CMO registration** | **← This is what MetaCheck does** |
| 7 | Track foreign plays | Soundcharts, Chartmetric |
| 8 | Recover unclaimed royalties | Muserk, Claimy |

## Where MetaCheck fits

MetaCheck lives at **step 6** — the exact point where the chain breaks for
~95% of independent artists. It's the bridge between *distribution* and
*royalty collection* that nobody has made accessible.

Every feature in this repo maps back to a break in the flow above:

- **Composer / publisher validation** → the composition can be registered at a
  CMO at all (steps 1–2, 4).
- **CMO registration check** (`validator/cmo.py`) → confirms the work is
  actually on file so the SACEM → SOCAN → you chain can complete (step 6).
- **ISRC format + consistency** (`validator/rules.py`) → the CMO can match
  streams back to the artist.
- **Royalty-at-risk estimate** (`validator/royalty.py`) → quantifies the
  mechanical royalties left in the black box when any of the above is missing.

## The pitch line

> **DistroKid gets your music on Spotify. MetaCheck makes sure you actually
> get paid for it — everywhere it plays.**

---

Repo: https://github.com/osmanmahdi1728/metacheck.git
