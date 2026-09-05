/* Argus mark: an eye whose iris is a node-link cluster.

   Two ideas the product actually rests on, in one shape. Argus Panoptes was
   the hundred-eyed watchman, so the outer form is an eye; the pupil is the
   transaction under investigation and the three spokes are the entity-graph
   links the Graph Builder pulls in around it -- watching, and watching the
   *connections*, which is the thing that separates this from a plain scorer.

   Drawn as inline SVG rather than an emoji or a bitmap so it stays crisp at
   every size, takes the brand gradient, and renders identically on every OS.
   Geometry was picked by rendering it at 72 / 38 / 22px against the real
   sidebar and keeping the version that still read as an eye at 22: nodes sit
   clear of the lid so they don't merge into the outline when it shrinks. */

export function LogoMark({ size = 40 }: { size?: number }) {
  const gid = `argus-mark-${size}`;
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 48 48"
      fill="none"
      role="img"
      aria-label="Argus"
    >
      <defs>
        <linearGradient id={gid} x1="5" y1="11" x2="43" y2="37" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#cdbfff" />
          <stop offset="100%" stopColor="#7a58ec" />
        </linearGradient>
      </defs>

      {/* lid */}
      <path
        d="M3.4 24C9.5 14 16.4 9 24 9s14.5 5 20.6 15C38.5 34 31.6 39 24 39S9.5 34 3.4 24Z"
        fill="none"
        stroke={`url(#${gid})`}
        strokeWidth="2.8"
        strokeLinejoin="round"
      />

      {/* graph links */}
      <path
        d="M24 24 24 15.8M24 24 31.2 27.9M24 24 16.8 27.9"
        stroke={`url(#${gid})`}
        strokeWidth="2"
        strokeLinecap="round"
      />

      {/* neighbour nodes */}
      <circle cx="24" cy="15.8" r="2.5" fill="#cdbfff" />
      <circle cx="31.2" cy="27.9" r="2.5" fill="#cdbfff" />
      <circle cx="16.8" cy="27.9" r="2.5" fill="#cdbfff" />

      {/* the transaction under investigation */}
      <circle cx="24" cy="24" r="4.3" fill="#efe9ff" />
    </svg>
  );
}

export function LogoLockup() {
  return (
    <div className="logo-lockup">
      <LogoMark size={46} />
      <div className="logo-text">
        <span className="logo-word">Argus</span>
        <span className="logo-sub">Fraud investigation</span>
      </div>
    </div>
  );
}
