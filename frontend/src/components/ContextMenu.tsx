import { Ban, Check } from 'lucide-react';

import type { BoxStatus, DetectionBox } from '../types';

export interface CanvasContextMenuState {
  boxId: string;
  x: number;
  y: number;
}

interface ContextMenuProps {
  contextMenu: CanvasContextMenuState;
  boxes: DetectionBox[];
  symbolNames: string[];
  onMarkBox: (boxId: string, status: BoxStatus) => void;
  onChangeBoxType: (boxId: string, symbolName: string) => void;
  onClose: () => void;
}

export function ContextMenu({
  contextMenu,
  boxes,
  symbolNames,
  onMarkBox,
  onChangeBoxType,
  onClose,
}: ContextMenuProps) {
  const currentSymbolName = boxes.find((box) => box.id === contextMenu.boxId)?.symbolName ?? '';

  return (
    <div
      className="fixed z-50 w-44 rounded border border-white/10 bg-[#17171b] p-2 shadow-2xl"
      style={{ left: contextMenu.x, top: contextMenu.y }}
      onMouseLeave={onClose}
    >
      <button
        type="button"
        className="flex w-full items-center gap-2 rounded px-2 py-2 text-left text-sm hover:bg-white/10"
        onClick={() => {
          onMarkBox(contextMenu.boxId, 'confirmed');
          onClose();
        }}
      >
        <Check className="h-4 w-4" />
        Potwierdź
      </button>
      <button
        type="button"
        className="flex w-full items-center gap-2 rounded px-2 py-2 text-left text-sm hover:bg-white/10"
        onClick={() => {
          onMarkBox(contextMenu.boxId, 'rejected');
          onClose();
        }}
      >
        <Ban className="h-4 w-4" />
        Odrzuć
      </button>
      <select
        className="mt-2 w-full rounded bg-black px-2 py-2 text-sm"
        value={currentSymbolName}
        onChange={(event) => {
          onChangeBoxType(contextMenu.boxId, event.target.value);
          onClose();
        }}
      >
        {symbolNames.map((name) => (
          <option key={name} value={name}>
            {name}
          </option>
        ))}
      </select>
    </div>
  );
}
