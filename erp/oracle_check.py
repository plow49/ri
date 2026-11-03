"""Read-only connectivity check. Never logs credentials or creates tables."""
import getpass
import sys
import oracledb

def main():
    print('Oracle 연결 확인 — 테이블을 생성하거나 데이터를 변경하지 않습니다.')
    host=input('서버 주소: ').strip()
    port=int(input('포트 [1521]: ').strip() or '1521')
    service=input('서비스명: ').strip()
    user=input('사용자명: ').strip()
    password=getpass.getpass('비밀번호 (저장하지 않음): ')
    try:
        with oracledb.connect(user=user,password=password,host=host,port=port,service_name=service,tcp_connect_timeout=10) as connection:
            with connection.cursor() as cursor:
                cursor.execute('SELECT 1 FROM DUAL')
                if cursor.fetchone()!=(1,): raise RuntimeError('Unexpected query result')
            print('PASS: Oracle 인증 및 SELECT 1 FROM DUAL 성공. 서버 버전:',connection.version)
            print('스키마 생성 권한과 ERP 업무 처리는 별도 검증이 필요합니다.')
        return 0
    except oracledb.Error as exc:
        error=exc.args[0]
        print('FAIL: Oracle 연결 실패. 오류 코드:',getattr(error,'full_code','UNKNOWN'))
        return 1
if __name__=='__main__': sys.exit(main())
