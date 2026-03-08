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
    return "닉네임은 한글, 영문, 숫자만 입력 가능합니다.";
  }

  if (length > 16) {
    return "닉네임은 한글 10자, 영문/숫자 16자 이내로 입력해주세요.";
  }

  return "";
}
