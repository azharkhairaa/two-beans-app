import { h } from 'vue'

// ikon garis 24x24 yang mengikuti currentColor, dirender lewat h() sehingga tidak perlu v-html
const c = (cx, cy, r) => ['circle', { cx, cy, r }]
const p = (d) => ['path', { d }]
const r = (x, y, width, height, rx = 0) => ['rect', { x, y, width, height, rx }]

const ICONS = {
  // menu
  dashboard: [r(3, 3, 7, 9, 1.5), r(14, 3, 7, 5, 1.5), r(14, 12, 7, 9, 1.5), r(3, 16, 7, 5, 1.5)],
  grid: [r(3, 3, 18, 18, 2), p('M3 9h18M3 15h18M9 3v18M15 3v18')],
  box: [p('M12 2 2 7l10 5 10-5-10-5z'), p('M2 17l10 5 10-5'), p('M2 12l10 5 10-5')],
  swap: [p('M7 4 3 8l4 4'), p('M3 8h14'), p('M17 20l4-4-4-4'), p('M21 16H7')],
  truck: [p('M3 6h10v10H3z'), p('M13 10h4l4 3v3h-8'), c(7, 18, 2), c(17, 18, 2)],
  clipboard: [r(5, 4, 14, 17, 2), r(9, 2, 6, 4, 1), p('M9 11h6M9 15h4')],
  cart: [c(9, 20, 1.5), c(18, 20, 1.5), p('M2 3h3l2.6 12.2a1.5 1.5 0 0 0 1.5 1.2h8.8a1.5 1.5 0 0 0 1.5-1.1L21 8H6.2')],
  receipt: [p('M5 3h14v18l-3-2-2 2-2-2-2 2-2-2-3 2z'), p('M9 8h6M9 12h6M9 16h3')],
  package: [
    p('M21 16V8a2 2 0 0 0-1-1.7l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.7l7 4a2 2 0 0 0 2 0l7-4a2 2 0 0 0 1-1.7z'),
    p('M3.3 7 12 12l8.7-5M12 22V12M7.5 4.2l9 5.2'),
  ],
  users: [c(9, 7, 4), p('M3 21v-2a4 4 0 0 1 4-4h4a4 4 0 0 1 4 4v2'), p('M16 3.1a4 4 0 0 1 0 7.8'), p('M21 21v-2a4 4 0 0 0-3-3.9')],
  'map-pin': [p('M12 21s-7-6.1-7-11.2a7 7 0 0 1 14 0C19 14.9 12 21 12 21z'), c(12, 9.8, 2.4)],
  tag: [p('M20.6 13.4 13.4 20.6a2 2 0 0 1-2.8 0L3 13V3h10l7.6 7.6a2 2 0 0 1 0 2.8z'), c(7.5, 7.5, 1.5)],
  factory: [p('M3 21V10l6 4v-4l6 4V4h6v17z'), p('M2 21h20')],
  'user-check': [c(9, 7, 4), p('M3 21v-2a4 4 0 0 1 4-4h4a4 4 0 0 1 4 4v2'), p('M16 11l2 2 4-4')],

  // antarmuka
  coffee: [p('M17 8h1a4 4 0 0 1 0 8h-1'), p('M3 8h14v9a4 4 0 0 1-4 4H7a4 4 0 0 1-4-4z'), p('M6 2v3M10 2v3M14 2v3')],
  user: [p('M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2'), c(12, 7, 4)],
  logout: [p('M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4'), p('M16 17l5-5-5-5'), p('M21 12H9')],
  menu: [p('M4 6h16M4 12h16M4 18h16')],
  close: [p('M18 6 6 18M6 6l12 12')],
  eye: [p('M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z'), c(12, 12, 3)],
  'eye-off': [
    p('M3 3l18 18'),
    p('M10.6 5.1A10 10 0 0 1 12 5c6.5 0 10 7 10 7a17.7 17.7 0 0 1-3.2 4.2'),
    p('M6.6 6.6C3.8 8.5 2 12 2 12s3.5 7 10 7a9.8 9.8 0 0 0 5.4-1.6'),
    p('M9.9 9.9a3 3 0 0 0 4.2 4.2'),
  ],
  'arrow-left': [p('M19 12H5'), p('M12 19l-7-7 7-7')],
  check: [p('M20 6 9 17l-5-5')],
  alert: [c(12, 12, 9), p('M12 7.5v5M12 16.2v.3')],
  info: [c(12, 12, 9), p('M12 16v-4.5M12 7.8v.3')],
  lock: [r(4, 11, 16, 10, 2), p('M8 11V7a4 4 0 0 1 8 0v4')],
  search: [c(11, 11, 7), p('M20 20l-3.8-3.8')],
  clock: [c(12, 12, 9), p('M12 7v5l3.2 2')],
}

export default {
  name: 'AppIcon',
  props: {
    name: { type: String, required: true },
    size: { type: [Number, String], default: 20 },
    stroke: { type: [Number, String], default: 2 },
  },
  setup(props) {
    return () =>
      h(
        'svg',
        {
          class: 'app-icon',
          width: props.size,
          height: props.size,
          viewBox: '0 0 24 24',
          fill: 'none',
          stroke: 'currentColor',
          'stroke-width': props.stroke,
          'stroke-linecap': 'round',
          'stroke-linejoin': 'round',
          'aria-hidden': 'true',
          focusable: 'false',
        },
        (ICONS[props.name] || ICONS.info).map(([tag, attrs]) => h(tag, attrs)),
      )
  },
}
