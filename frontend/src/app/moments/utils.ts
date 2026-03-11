import { EditorState } from "./types";

export const todayString = () => new Date().toISOString().slice(0, 10);

export const emptyEditorState = (): EditorState => ({
  id: null,
  title: "",
  content: "",
  entry_date: todayString(),
  cover_image_path: null,
  linked_places: [],
});

export const readFileAsDataUrl = (file: File) =>
  new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(typeof reader.result === "string" ? reader.result : "");
    reader.onerror = () => reject(new Error("file-read-failed"));
    reader.readAsDataURL(file);
  });

/** JPEG EXIF에서 GPS 좌표를 추출합니다. GPS 없으면 null 반환. */
export const readExifGps = (file: File): Promise<{ latitude: number; longitude: number } | null> =>
  new Promise((resolve) => {
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const buf = reader.result as ArrayBuffer;
        const view = new DataView(buf);
        // JPEG SOI marker 확인
        if (view.getUint16(0) !== 0xffd8) { resolve(null); return; }
        let offset = 2;
        while (offset < view.byteLength - 4) {
          const marker = view.getUint16(offset);
          const length = view.getUint16(offset + 2);
          // APP1 (0xFFE1) = EXIF 세그먼트
          if (marker === 0xffe1) {
            const exifHeader = String.fromCharCode(
              view.getUint8(offset + 4), view.getUint8(offset + 5),
              view.getUint8(offset + 6), view.getUint8(offset + 7),
            );
            if (exifHeader === "Exif") {
              const tiffOffset = offset + 10;
              const littleEndian = view.getUint16(tiffOffset) === 0x4949;
              const getUint16 = (o: number) => view.getUint16(tiffOffset + o, littleEndian);
              const getUint32 = (o: number) => view.getUint32(tiffOffset + o, littleEndian);
              // IFD0 탐색
              const ifd0 = getUint32(4);
              const ifd0Count = getUint16(ifd0);
              let gpsIfdOffset = 0;
              for (let i = 0; i < ifd0Count; i++) {
                const entryOffset = ifd0 + 2 + i * 12;
                const tag = getUint16(entryOffset);
                if (tag === 0x8825) { gpsIfdOffset = getUint32(entryOffset + 8); break; }
              }
              if (!gpsIfdOffset) { resolve(null); return; }
              // GPS IFD 탐색
              const gpsCount = getUint16(gpsIfdOffset);
              const gpsData: Record<number, number[]> = {};
              for (let i = 0; i < gpsCount; i++) {
                const entryOffset = gpsIfdOffset + 2 + i * 12;
                const tag = getUint16(entryOffset);
                const type = getUint16(entryOffset + 2);
                const count = getUint32(entryOffset + 4);
                const valueOffset = getUint32(entryOffset + 8);
                // tag 1=LatRef, 2=Lat, 3=LngRef, 4=Lng
                if (type === 5 && count === 3) { // RATIONAL × 3
                  const vals: number[] = [];
                  for (let j = 0; j < 3; j++) {
                    const num = getUint32(valueOffset + j * 8);
                    const den = getUint32(valueOffset + j * 8 + 4);
                    vals.push(den !== 0 ? num / den : 0);
                  }
                  gpsData[tag] = vals;
                } else if (type === 2) { // ASCII
                  gpsData[tag] = [view.getUint8(tiffOffset + valueOffset)];
                }
              }
              const toDecimal = (vals: number[]) =>
                vals[0] + vals[1] / 60 + vals[2] / 3600;
              if (!gpsData[2] || !gpsData[4]) { resolve(null); return; }
              let lat = toDecimal(gpsData[2]);
              let lng = toDecimal(gpsData[4]);
              if (gpsData[1]?.[0] === 83 /* 'S' */) lat = -lat;
              if (gpsData[3]?.[0] === 87 /* 'W' */) lng = -lng;
              resolve({ latitude: lat, longitude: lng });
              return;
            }
          }
          offset += 2 + length;
        }
        resolve(null);
      } catch {
        resolve(null);
      }
    };
    reader.onerror = () => resolve(null);
    reader.readAsArrayBuffer(file);
  });
