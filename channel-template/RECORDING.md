# Recording guide (adapt to your camera, room and country)

## Voice (the most important part)
- Quiet room with soft furnishings (curtains, a bed, a wardrobe full of clothes). A bare room rings for ~0.5 s,
  and loudness normalisation for YouTube (-14 LUFS) makes that echo about 7 dB louder.
- Phone or mic **10-15 cm from the mouth**, slightly to one side (no plosives). A lavalier mic is the single
  biggest improvement. Turn off the phone's "enhance" / noise reduction.
- Start every file with **3 s of silence**, then **clap once** (syncs the phone track to the camera).
- One teleprompter line per breath. If you slip, stop for 2 s and re-read that line from the start.
- WAV (48 kHz) if the app allows it, otherwise m4a. Files: `raw/voice.wav`, `raw/cam-<shot>.m4a`.

## Camera (talking to camera, fixed)
| Setting | Value |
|---|---|
| Video system | match your mains: 50 Hz countries -> PAL, 25p (shutter 1/50); 60 Hz -> NTSC, 30p (shutter 1/60). Don't mix frame rates in one episode. Set `[video] fps` to match. |
| Exposure | manual (M): shutter as above, f/4 talking, f/5.6-8 for table-top demos, ISO as low as the light allows |
| White balance | fixed Kelvin (or custom WB from a white sheet), never auto |
| Picture profile | off (no log) |
| Focus | continuous AF with face / eye priority; manual focus for demos |
| Stabilisation | off on a tripod |
| Zebra | 100+: a touch of zebra on the forehead is right |
| Camera audio | backup only |

## Light
- Key light 45° in front, 70-100 cm from the face, slightly above the eyes, on the side of the **clean wall**
  (so shadows don't fall where CG will go). Optional coloured rim light behind, only on hair and shoulders.
- Turn off ceiling lights and coloured LED strips. Plain top without logos or fine stripes.
- Sit off-centre with a clean wall on the other side for CG; 1-1.5 m from the wall.
- Nothing private on screens or shelves.

## Test first
Record a 20 s test clip (`raw/test.mp4`) before the first real take. Claude measures brightness and white
balance from frames and suggests concrete changes, with before/after frames.
