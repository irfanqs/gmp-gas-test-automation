[![English](https://img.shields.io/badge/Language-English-2563EB)](README.md) [![한국어](https://img.shields.io/badge/언어-한국어-0B6E4F)](README.kr.md)

# GMP 가스 시험 자동화 - 온라인 OCR

스캔된 한국어 GMP 가스 시험 PDF를 검토 가능한 데이터, Excel 통합 문서 및 다운로드 가능한 차트로 변환하는 Flask 웹 애플리케이션입니다.

지원 측정 항목:

- 유분 측정 (`유분 측정 일지`)
- 수분 측정 (`수분 측정 일지`)
- 부유입자 측정 (`부유입자 측정 일지`)

## 주요 기능

- Anthropic Claude를 이용한 온라인 OCR
- 영어 및 한국어 인터페이스
- 한 번에 하나의 측정 종류에 대해 여러 PDF를 누적 선택 가능
- 중복 파일 선택 자동 제외 및 추출 전 선택 파일 삭제 가능
- 내보내기 전 OCR 결과 검토 및 수정
- XlsxWriter를 이용한 Excel 생성
- 경고/허용 기준을 선 계열로 표시하는 세로 막대형 차트
- JPG 차트 및 통합 차트 PDF 내보내기
- 내부 작업 ID가 제거된 깔끔한 다운로드 파일명

## 온라인 OCR

`http://127.0.0.1:5005/online`을 엽니다.

이 브랜치는 `5005` 포트를 사용합니다. 함께 제공되는 `gmp-offline` 브랜치는 `5006` 포트를 사용합니다. 두 애플리케이션을 동시에 실행하려면 각각 별도의 checkout 또는 Git worktree에서 실행하십시오.

온라인 OCR은 렌더링된 PDF 페이지를 Anthropic으로 전송합니다. 마지막 페이지의 왼쪽 `Performed by` 날짜 영역도 확대하여 손글씨 날짜 인식에 사용하며, 부유입자 측정에서는 손글씨 숫자 확인을 위한 표 확대 이미지도 함께 사용합니다. Claude가 반환한 구조화 JSON은 검증 후 검토 표에 표시됩니다.

로컬 `.env` 파일을 생성하십시오.

```env
ANTHROPIC_API_KEY=your_anthropic_api_key
```

`.env` 파일은 Git에서 제외됩니다. API 키를 커밋하거나 공유하지 마십시오.

## 시스템 요구 사항

- Python 3.10 이상
- 스캔 PDF 페이지 렌더링을 위한 Poppler
- Anthropic API 사용을 위한 인터넷 연결

Poppler 설치:

```bash
# macOS
brew install poppler

# Ubuntu 또는 Debian
sudo apt install poppler-utils
```

Windows에서는 Poppler를 설치한 후 `Library\bin` 디렉터리를 `PATH`에 추가하십시오.

## 설치 및 실행

### 자동 실행

macOS:

```bash
./START_MAC.sh
```

Windows:

```bat
START_WINDOWS.bat
```

실행 스크립트는 `.venv`를 생성하고 `requirements.txt`의 패키지를 설치한 다음 브라우저를 열고 애플리케이션을 `5005` 포트에서 실행합니다.

`START_WINDOWS.bat`는 `main` 브랜치의 파일과 동일하게 유지됩니다. Windows에서 처음 실행할 때 `.env`를 생성하고 Anthropic API 키를 요청합니다. 키는 로컬에 `ANTHROPIC_API_KEY`로 저장되며 `.env`에서 값을 삭제하지 않는 한 이후 실행에서는 다시 요청하지 않습니다.

### 수동 실행

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```

Windows 가상 환경 활성화:

```bat
.venv\Scripts\activate
```

`http://127.0.0.1:5005`를 엽니다. 루트 경로는 `/online`으로 이동합니다.

## 사용 절차

1. 유분, 수분 또는 부유입자 측정을 선택합니다.
2. 같은 측정 종류의 PDF를 하나 이상 선택하거나 드래그합니다.
3. 필요한 경우 PDF를 추가로 선택합니다. 새 파일은 기존 목록에 추가됩니다.
4. 불필요한 파일은 빨간색 X 버튼으로 제거합니다.
5. **데이터 추출**을 선택합니다.
6. 특히 손글씨 날짜와 측정값을 검토하고 필요한 값을 수정합니다.
7. **Excel 및 차트 생성**을 선택합니다.
8. Excel 통합 문서, 통합 차트 PDF 또는 개별 JPG 차트를 다운로드합니다.

Excel 생성 단계에서는 Claude를 호출하지 않습니다. Anthropic은 **데이터 추출** 중에만 사용됩니다.

## 출력 파일

각 내보내기에는 현재 업로드 배치에서 검토한 데이터만 포함됩니다. 이전 로컬 데이터는 생성되는 통합 문서에 추가되지 않습니다.

유분 측정 통합 문서:

- `데이터`
- `간소화된 데이터`
- `피벗 차트`

수분 측정 통합 문서:

- `데이터`
- `간소화된 데이터`
- `피벗 차트`

부유입자 측정 통합 문서:

- `데이터`
- `Pivot 0.5`
- `Pivot 5.0`

부유입자 측정은 `0.5 μm`와 `5.0 μm` JPG를 각각 생성합니다. 차트는 원본 데이터 표 아래 두 개의 빈 행을 두고 자동 배치됩니다.

생성된 파일은 `outputs/`에 저장됩니다. 서버 파일명에는 충돌 방지를 위한 내부 작업 ID가 포함되지만 브라우저 다운로드에는 측정 일지 이름만 표시됩니다.

## 로컬 데이터

검토된 데이터는 다음 로컬 데이터베이스에도 저장됩니다.

```text
data/gas_test_logs.sqlite3
```

데이터베이스는 로컬 이력으로 유지되지만 현재 Excel 내보내기에는 병합되지 않습니다. 이력을 삭제하려면 애플리케이션을 종료한 후 `data/gas_test_logs.sqlite3`을 삭제하십시오.

업로드한 임시 PDF는 OCR 처리 후 삭제됩니다. 다음 경로는 Git에서 제외됩니다.

- `.env`
- `.venv/`
- `uploads/`
- `outputs/`
- `data/`

## 개인정보 보호

애플리케이션은 렌더링된 PDF 페이지와 필요한 확대 영역을 Anthropic으로 전송합니다. PDF 렌더링, 결과 검토, 저장, Excel 생성, JPG 생성 및 차트 PDF 생성은 로컬에서 수행됩니다.

## 검증

OCR을 실행하지 않고 기본 문법 검사를 수행하려면 다음 명령을 사용합니다.

```bash
.venv/bin/python -m py_compile app.py online_client.py parsers.py storage.py excel_generator.py
node --check static/app.js
```

전체 흐름을 검증하려면 인터페이스에서 샘플 PDF를 업로드하고 검토 표를 확인한 다음 통합 문서를 생성하여 각 Excel 시트와 차트를 확인하십시오.

## 문제 해결

### `422 Unprocessable Entity`

OCR은 완료되었지만 유효한 측정 데이터가 파싱되지 않은 상태입니다. 선택한 측정 종류와 PDF 종류가 일치하는지 확인하고, 코드 변경 사항을 받은 후에는 Flask 서버를 다시 시작하십시오. 온라인 OCR은 Anthropic이 반환하는 구조화 JSON을 사용합니다.

### `ANTHROPIC_API_KEY is not configured`

`.env`에 `ANTHROPIC_API_KEY`를 추가한 후 애플리케이션을 다시 시작하십시오.

### PDF 렌더링 실패

Poppler를 설치하고 `pdftoppm`을 `PATH`에서 실행할 수 있는지 확인하십시오.

### 브라우저에 이전 화면이 표시됨

Flask 프로세스를 다시 시작하고 페이지를 새로고침하십시오. 정적 JavaScript URL에는 캐시 무효화 버전이 포함되지만, 실행 중인 프로세스는 재시작 전까지 이전 템플릿을 제공할 수 있습니다.

## 주요 파일

- `app.py`: 온라인 화면, 데이터 추출, 파일 생성 및 다운로드를 위한 Flask 경로
- `online_client.py`: Anthropic OCR 및 구조화 JSON 프롬프트
- `parsers.py`: 구조화 JSON 및 HTML/Markdown 표 파서
- `excel_generator.py`: XlsxWriter 통합 문서 및 Matplotlib JPG/PDF 차트 생성
- `storage.py`: 로컬 SQLite 이력 저장
- `templates/index.html`: 애플리케이션 인터페이스
- `static/app.js`: 업로드 관리, 검토 표, 파일 생성 및 다운로드
