"use client";

import ForceGraph2D from "react-force-graph-2d";
import type { ComponentProps, MutableRefObject } from "react";

type FGProps = ComponentProps<typeof ForceGraph2D> & {
  // next/dynamic does not forward refs, so the graph handle travels as a prop.
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  graphRef?: MutableRefObject<any>;
};

export default function ForceGraph({ graphRef, ...props }: FGProps) {
  return <ForceGraph2D ref={graphRef} {...props} />;
}
