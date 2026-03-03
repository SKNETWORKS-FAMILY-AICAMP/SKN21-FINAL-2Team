# 자동 시작 스트리밍 말풍선 누락 이슈 수정 (2026-03-04)

## 증상
- 새 채팅방 자동 시작(팝업/북마크 진입)에서 파이프라인은 보이지만 AI 말풍선이 늦게 뜨거나 안 뜨는 현상.
- 일반 수동 질문에서는 토큰 스트리밍이 정상인데, 자동 시작에서만 체감상 스트리밍이 깨지는 현상.

## 원인
1. 프론트의 토큰 반영 로직이 `placeholder AI 메시지`를 전제로 동작.
   - 자동 시작 흐름에서 상태 갱신 타이밍에 따라 placeholder가 유실되면,
     토큰 이벤트가 와도 기존 메시지 `map` 갱신이 실패하여 말풍선이 안 생김.
2. SSE 파서가 라인 단위(`\n`) 중심이라 이벤트 경계가 애매한 청크에서 이벤트 누락 가능성이 있음.

## 수정 내용
1. `frontend/src/components/chat/ChatHome.tsx`
   - `onToken`에서 placeholder를 찾지 못하면 AI 메시지를 즉시 `append`하도록 변경.
   - `onDone` 시에도 파이프라인을 숨기도록 보강.
2. `frontend/src/services/api.ts`
   - SSE 파서를 이벤트 단위(`\n\n`)로 변경.
   - 남은 버퍼(`buffer`)도 종료 시 1회 파싱.
3. `backend/app/api/chat.py`, `backend/app/schemas/chat.py`
   - 숫자 결측값 정책을 `0`으로 통일.
   - `0`은 값 없음으로 해석.
   - 주요 대상: `place_id`, `latitude`, `longitude`.
4. 중복 코드 모듈화(2026-03-04 추가)
   - `frontend/src/components/chat/ChatHome.tsx`
     - 자동 시작 전송/일반 전송 로직을 `streamMessageToRoom`으로 통합.
     - 방 제목 갱신 공통 함수 `updateRoomTitle`로 분리.
   - `frontend/src/services/api.ts`
     - 위치 문자열 파싱을 `parseLocationToCoords`로 공통화.
     - 요청 body 생성을 `buildChatRequestBody`로 공통화.
   - `backend/app/api/chat.py`
     - `/ask`, `/ask/stream` 공통 전처리 함수 분리:
       - `_get_owned_room_or_404`
       - `_save_human_message_if_needed`
       - `_build_graph_inputs`
5. 자동 시작 프롬프트/호출 단일화(2026-03-04 추가)
   - `backend/app/services/prompts.py`
     - `AUTO_START_PROMPT`, `AUTO_START_PLACE_PROMPT` 추가
   - `backend/app/services/auto_start_prompt.py`
     - 자동 시작 프롬프트 렌더러 추가
   - `backend/app/api/chat.py`
     - `POST /api/chat/rooms/{room_id}/autostart/stream` 추가
     - 자동 시작은 백엔드에서 프롬프트 생성 후 즉시 스트리밍 실행
   - `frontend/src/services/api.ts`
     - `sendAutoStartChatRoomStream` 추가
   - `frontend/src/components/chat/ChatHome.tsx`
     - 로컬 prompt builder 제거
     - auto start는 신규 API로만 호출
6. 여행 인원 입력 모델 변경(2026-03-04 추가)
   - `groupSize` 문자열 제거
   - `adultCount`, `childCount` 기반으로 저장/전달
   - 연관 파일:
     - `frontend/src/components/chat/TripContextModal.tsx`
     - `frontend/src/components/chat/ChatHome.tsx`
     - `frontend/src/components/Sidebar.tsx`
     - `frontend/src/components/landing/Destinations.tsx`
     - `backend/app/schemas/chat.py` (`adult_count`, `child_count`)

## 정책
- 숫자 필드는 가능하면 `null` 대신 `0`을 사용한다.
- `0`은 비즈니스적으로 값 없음(미정/미지정)을 의미한다.

## 검증
- 백엔드: `tests/test_chat_stream.py` 통과. (autostart/stream 케이스 포함)
- 프론트: `tests/ChatHome.stt-permission.test.tsx` 통과.
