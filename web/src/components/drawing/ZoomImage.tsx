import { Maximize2, Minus, Plus } from 'lucide-react'
import { TransformComponent, TransformWrapper, useControls } from 'react-zoom-pan-pinch'

import { Button } from '@/components/ui/button'

function Controls() {
  const { zoomIn, zoomOut, resetTransform } = useControls()
  return (
    <div className="absolute top-3 right-3 z-10 flex gap-1 rounded-lg border bg-background/90 p-1 shadow-sm backdrop-blur">
      <Button variant="ghost" size="icon-sm" aria-label="Thu nhỏ" onClick={() => zoomOut()}>
        <Minus />
      </Button>
      <Button variant="ghost" size="icon-sm" aria-label="Vừa khung" onClick={() => resetTransform()}>
        <Maximize2 />
      </Button>
      <Button variant="ghost" size="icon-sm" aria-label="Phóng to" onClick={() => zoomIn()}>
        <Plus />
      </Button>
    </div>
  )
}

/** Drawing viewer: wheel/pinch to zoom, drag to pan. ``src`` changes reset the view. */
export function ZoomImage({ src, alt }: { src: string; alt: string }) {
  return (
    <div className="relative overflow-hidden rounded-xl border bg-white">
      <TransformWrapper key={src} minScale={0.5} maxScale={6} centerOnInit wheel={{ step: 0.15 }}>
        <Controls />
        <TransformComponent wrapperClass="!h-[min(62vh,560px)] !w-full" contentClass="!h-full !w-full">
          <img src={src} alt={alt} className="h-full w-full object-contain select-none" draggable={false} />
        </TransformComponent>
      </TransformWrapper>
    </div>
  )
}
