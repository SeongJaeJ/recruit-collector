# recruit-collector

공식 채용 홈페이지를 직접 확인해서 프론트엔드 개발자에게 맞는 공고를 텔레그램 채널로 보내는 수집기입니다.

## 동작 방식

1. 대기업, 금융, 증권, 제조, 건설, 정유, 플랫폼 기업의 공식 채용 페이지에 접속합니다.
2. 공고명, 목록 본문, 상세 페이지, 구조화 데이터의 텍스트를 확인합니다.
3. 프론트엔드, 웹, React, Vue, TypeScript 등 관련 키워드를 기준으로 공고를 필터링합니다.
4. 마감일 또는 채용 상태를 추출합니다.
5. Telegram Bot API로 채널에 리포트를 전송합니다.

## 설정

`.env.example`을 참고해서 `.env`를 만듭니다.

```env
TELEGRAM_KEY=1234567890:replace_with_your_bot_token
TELEGRAM_CHAT_ID=-1001234567890
```

`.env`에는 실제 봇 토큰이 들어가므로 커밋하지 않습니다.

## Docker 실행

이미지를 빌드합니다.

```powershell
docker compose build
```

일부 회사만 확인하는 빠른 테스트입니다.

```powershell
docker compose run --rm recruit-collector --dry-run --max-companies 5
```

실제 텔레그램 전송을 한 번 테스트합니다.

```powershell
docker compose run --rm recruit-collector --once
```

매일 KST 오전 10시에 자동 전송되도록 백그라운드 실행합니다.

```powershell
docker compose up -d
```

로그 확인:

```powershell
docker compose logs -f
```

## 로컬 실행

Docker 없이도 Python으로 직접 실행할 수 있습니다.

```powershell
python job_reporter.py --dry-run --max-companies 5
python job_reporter.py
python job_reporter.py --schedule
```

## 테스트

```powershell
python -m unittest
```
