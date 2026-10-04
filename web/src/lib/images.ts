import { toast } from 'sonner'

export const IMAGE_TYPES = ['image/png', 'image/jpeg', 'image/webp', 'image/gif']
const MAX_IMAGE_BYTES = 20 * 1024 * 1024

/** The file if it is a problem image the server accepts; otherwise explain and return null. */
export function acceptImage(file: File | undefined | null): File | null {
  if (!file) return null
  if (!IMAGE_TYPES.includes(file.type)) {
    toast.error('Ảnh phải có định dạng PNG, JPG, WEBP hoặc GIF.')
    return null
  }
  if (file.size > MAX_IMAGE_BYTES) {
    toast.error('Ảnh lớn hơn 20 MB; hãy cắt gọn vùng chứa đề bài.')
    return null
  }
  return file
}
