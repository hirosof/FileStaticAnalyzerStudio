#define NOMINMAX
#include <locale>

int main() {

	// 日本語ロケールに設定
	setlocale( LC_ALL, "Japanese" );

	wprintf( L"これはFileStaticAnalyzerStudio向けのサンプルEXEファイル(native)です。\n" );

	return 0;
}