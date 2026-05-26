import * as PIXI from "pixi.js";
import { Cow, CowBreed } from "./entities/Cow";

const MAP_W = 1448;
const MAP_H = 1086;

export const WALK_ZONE = { x: 310, y: 455, width: 880, height: 400 };

// 9 adults (scale 0.55) + 7 babies (scale 0.38) — breeds distributed across all 4 types
const SPAWNS: { x: number; y: number; scale: number; breed: CowBreed }[] = [
  // adults
  { x: 430,  y: 600, scale: 0.55, breed: "angus"     },
  { x: 650,  y: 545, scale: 0.55, breed: "brahman"   },
  { x: 820,  y: 580, scale: 0.55, breed: "charolais" },
  { x: 1010, y: 635, scale: 0.55, breed: "wagyu"     },
  { x: 535,  y: 725, scale: 0.55, breed: "angus"     },
  { x: 755,  y: 770, scale: 0.55, breed: "brahman"   },
  { x: 960,  y: 810, scale: 0.55, breed: "charolais" },
  { x: 385,  y: 815, scale: 0.55, breed: "wagyu"     },
  { x: 1095, y: 735, scale: 0.55, breed: "angus"     },
  // babies
  { x: 490,  y: 650, scale: 0.38, breed: "brahman"   },
  { x: 710,  y: 610, scale: 0.38, breed: "charolais" },
  { x: 875,  y: 690, scale: 0.38, breed: "wagyu"     },
  { x: 630,  y: 800, scale: 0.38, breed: "angus"     },
  { x: 1055, y: 780, scale: 0.38, breed: "brahman"   },
  { x: 355,  y: 745, scale: 0.38, breed: "charolais" },
  { x: 848,  y: 845, scale: 0.38, breed: "wagyu"     },
];

export class Farm {
  private app: PIXI.Application;
  private cows: Cow[] = [];
  private cowContainer: PIXI.Container;

  constructor(canvas: HTMLCanvasElement) {
    this.app = new PIXI.Application({
      view: canvas,
      width: MAP_W,
      height: MAP_H,
      backgroundColor: 0x000000,
      antialias: false,
      resolution: 1,
    });

    // Background
    const bg = PIXI.Sprite.from("/asset/farm-01.png");
    bg.width = MAP_W;
    bg.height = MAP_H;
    this.app.stage.addChild(bg);

    // Cows
    this.cowContainer = new PIXI.Container();
    this.app.stage.addChild(this.cowContainer);

    for (const s of SPAWNS) {
      const cow = new Cow(s.x, s.y, s.scale, WALK_ZONE, s.breed);
      this.cows.push(cow);
      this.cowContainer.addChild(cow.sprite);
    }

    // Game loop: AI update + depth sort
    this.app.ticker.add((delta) => {
      const dt = delta / 60;
      for (let i = 0; i < this.cows.length; i++) {
        this.cows[i].update(dt, this.cows, i);
      }
      this.cowContainer.children.sort((a, b) => a.y - b.y);
    });
  }

  destroy() {
    this.app.destroy(false, { children: true });
  }
}
