export type GenderType = "male" | "female" | "other";

export function getNicknameValidationError(value: string): string {
  const hasSpecialChar = /[^ㄱ-ㅎㅏ-ㅣ가-힣a-zA-Z0-9]/.test(value);
  let length = 0;

  for (let i = 0; i < value.length; i += 1) {
    if (/[ㄱ-ㅎ|ㅏ-ㅣ|가-힣]/.test(value[i])) {
      length += 1.6;
    } else {
      length += 1;
    }
  }

  if (hasSpecialChar) {
    return "validation.nicknameSpecialChar";
  }

  if (length > 16) {
    return "validation.nicknameTooLong";
  }

  return "";
}
