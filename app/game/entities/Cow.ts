import * as PIXI from "pixi.js";

// Sprite sheets: 720x1100, 3 cols x 5 rows, each frame 240x220
const FRAME_W = 240;
const FRAME_H = 220;

const ROW = { idle: 0, walkLeft: 1, walkRight: 2, walkDown: 3, walkUp: 4 } as const;
type Dir = keyof typeof ROW;
type Axis = "h" | "v";

export type CowBreed = "angus" | "brahman" | "charolais" | "wagyu";

const BREED_SHEETS: Record<CowBreed, string> = {
  angus:     "/asset/sprite/cows/angus-cows.png",
  brahman:   "/asset/sprite/cows/brahman-cows.png",
  charolais: "/asset/sprite/cows/charolais-cows.png",
  wagyu:     "/asset/sprite/cows/wagyu-cows.png",
};

const SPEED = 60;
const SEP_RADIUS = 80;
const SEP_FORCE  = 100;
const ARRIVE_H   = 14;

function makeFrames(base: PIXI.BaseTexture, row: number): PIXI.Texture[] {
  return [0, 1, 2].map(
    (col) => new PIXI.Texture(base, new PIXI.Rectangle(col * FRAME_W, row * FRAME_H, FRAME_W, FRAME_H))
  );
}

export interface WalkZone { x: number; y: number; width: number; height: number; }

export class Cow {
  sprite: PIXI.AnimatedSprite;

  private allFrames: Record<Dir, PIXI.Texture[]>;
  private dir: Dir = "idle";

  px: number;
  py: number;
  private targetX: number;
  private targetY: number;
  private idleTimer = 0;
  private axis: Axis = "h";
  private zone: WalkZone;

  constructor(x: number, y: number, scale: number, zone: WalkZone, breed: CowBreed = "angus") {
    this.px = x;
    this.py = y;
    this.zone = zone;
    this.targetX = x;
    this.targetY = y;
    this.idleTimer = Math.random() * 2.5;

    const base = PIXI.BaseTexture.from(BREED_SHEETS[breed]);
    this.allFrames = {
      idle:      makeFrames(base, ROW.idle),
      walkLeft:  makeFrames(base, ROW.walkLeft),
      walkRight: makeFrames(base, ROW.walkRight),
      walkDown:  makeFrames(base, ROW.walkDown),
      walkUp:    makeFrames(base, ROW.walkUp),
    };

    this.sprite = new PIXI.AnimatedSprite(this.allFrames.idle);
    this.sprite.animationSpeed = 0.08 + Math.random() * 0.03;
    this.sprite.loop = true;
    this.sprite.anchor.set(0.5, 1);
    this.sprite.scale.set(scale);
    this.sprite.x = x;
    this.sprite.y = y;
    this.sprite.play();

    this.pickTarget();
  }

  update(dt: number, others: Cow[], selfIdx: number) {
    // ── Idle countdown ──
    if (this.idleTimer > 0) {
      this.idleTimer -= dt;
      this.setDir("idle");
      return;
    }

    const dx = this.targetX - this.px;
    const dy = this.targetY - this.py;
    const arrivedH = Math.abs(dx) < ARRIVE_H;
    const arrivedV = Math.abs(dy) < ARRIVE_H;

    // Fully arrived → idle then pick new target
    if (arrivedH && arrivedV) {
      this.idleTimer = Math.random() < 0.35 ? 1.5 + Math.random() * 3 : 0.3;
      this.pickTarget();
      this.setDir("idle");
      return;
    }

    // Switch axis when current axis is resolved
    if (this.axis === "h" && arrivedH) this.axis = "v";
    if (this.axis === "v" && arrivedV) this.axis = "h";

    // ── Velocity: move ONLY along current axis ──
    let vx = 0;
    let vy = 0;

    if (this.axis === "h") vx = Math.sign(dx) * SPEED;
    else                   vy = Math.sign(dy) * SPEED;

    // ── Separation force (only on the active axis to keep 4-dir strict) ──
    let sepX = 0, sepY = 0;
    for (let i = 0; i < others.length; i++) {
      if (i === selfIdx) continue;
      const ox = this.px - others[i].px;
      const oy = this.py - others[i].py;
      const d  = Math.sqrt(ox * ox + oy * oy);
      if (d < SEP_RADIUS && d > 0) {
        const s = SEP_FORCE * (1 - d / SEP_RADIUS);
        sepX += (ox / d) * s;
        sepY += (oy / d) * s;
      }
    }
    if (this.axis === "h") vx += sepX;
    else                   vy += sepY;

    // ── Clamp inside zone ──
    this.px = Math.max(this.zone.x, Math.min(this.zone.x + this.zone.width,  this.px + vx * dt));
    this.py = Math.max(this.zone.y, Math.min(this.zone.y + this.zone.height, this.py + vy * dt));

    this.sprite.x = this.px;
    this.sprite.y = this.py;

    // ── Face direction ──
    if (this.axis === "h") this.setDir(vx < 0 ? "walkLeft"  : "walkRight");
    else                   this.setDir(vy < 0 ? "walkUp"    : "walkDown");
  }

  get footY() { return this.py; }

  private setDir(dir: Dir) {
    if (this.dir === dir) return;
    this.dir = dir;
    this.sprite.textures = this.allFrames[dir];
    this.sprite.gotoAndPlay(0);
  }

  private pickTarget() {
    const margin = 40;
    this.targetX = this.zone.x + margin + Math.random() * (this.zone.width  - margin * 2);
    this.targetY = this.zone.y + margin + Math.random() * (this.zone.height - margin * 2);
    // Randomise which axis to tackle first so cows vary their paths
    this.axis = Math.random() < 0.5 ? "h" : "v";
  }
}
