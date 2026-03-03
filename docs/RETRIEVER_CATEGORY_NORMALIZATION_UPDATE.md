# Retriever 카테고리 정규화 업데이트 (2026-03-03)

## 변경 배경
- `places` 컬렉션의 payload는 `contenttypeid` 키를 기준으로 카테고리 필터링을 수행한다.
- 하지만 상위 노드(의도/플래너)에서 `숙소`, `카페`, `체험` 같은 별칭 카테고리가 들어올 수 있어 필터 미스가 발생할 수 있다.

## 적용 내용
- 파일: `backend/app/retrieval/place.py`
- `PlaceRetriever.get_instance().normalize_category()`를 추가하여 입력 카테고리를 `contenttypeid` 표준값으로 정규화한다.
- `_build_category_filter()`에서 정규화 결과를 사용해 `contenttypeid` 필터를 구성한다.
- `search_hybrid()`의 스코어 결합을 raw score 가중합에서 **RRF(rank 기반 결합)** 으로 변경한다.
- `PHOTOS_COLLECTION` 결과 병합 시 `point.id(UUID)`가 아닌 payload의 `contentid`를 기준으로 장소 단위로 합친다.
- `search_hybrid()` / `search_image()` 내부의 동기 호출(`download_image`, `encode`, `query_points`)을 `asyncio.to_thread`로 오프로딩한다.
- `retrieval_place()`에서 예외 발생 시 `search_results`/`nearby_places` 참조 오류가 나지 않도록 기본값을 선초기화한다.
- `retrieval_place()`의 사진 조회 필터 키를 `place_id`에서 `contentid`로 수정한다.
- `search_image()`의 그룹 키를 `place_id`에서 `contentid`로 수정한다.
- 대표 매핑:
  - `숙소` -> `숙박`
  - `카페` -> `음식점`
  - `체험` -> `레포츠`
  - `박물관`/`미술관` -> `문화시설`
  - `축제`/`공연` -> `축제공연행사`

## 테스트
- 파일: `backend/tests/test_retriever_category_normalization.py`
- 검증 항목:
  - 별칭 카테고리 정규화 성공
  - 미지원/빈 값 입력 시 `None` 반환
- 파일: `backend/tests/test_retriever_regression.py`
- 검증 항목:
  - `PHOTOS_COLLECTION` 병합 시 `contentid` 기반 place id 추출
  - retriever 초기화 실패 시 `retrieval_place()`가 `(None, [])`로 안전 반환

## 기대 효과
- 카테고리 필터 누락 감소
- 슬롯 표현 다양성에 대한 검색 안정성 향상
- 이기종 채널 점수 분포 차이로 인한 랭킹 왜곡 완화
- 이벤트 루프 블로킹 감소 및 동시 요청 처리 안정성 향상
