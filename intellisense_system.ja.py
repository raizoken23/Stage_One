"""
intellisense_system.py - Citadel Dossier System の適応型インテリセンスコア

概要:
このモジュールは、Citadel Dossier System の中央インテリジェンスハブとして機能し、
ソフトウェア開発ライフサイクルの評価と改善のためのAI駆動の支援を提供します。
さまざまな特化したAIコンポーネントを統合し、コードベースの健全性、システムログ、
および開発者の対話パターンに基づいて、インテリジェントで文脈化された
提案、フィードバック、および診断を提供します。

主な機能:
--------------------
1.  自動依存関係管理: システムの機能性を確保するために、必要なPythonライブラリ
    (例: numpy, psutil, sentence-transformers) をチェックし、インストールします。
2.  設定可能な操作: 'intellisense_config.json' からコアシステムパラメータ、指示、
    および開発者の好みを読み込んで管理し、適応的な振る舞いを可能にします。
3.  モジュラーAI統合 (Memoriaエコシステム): AIモジュールのサブシステム
    (MemoriaCore, Self-Reflection, Optimization Engine, Analysis Interface) を
    内部クラスとして統合し、メタ認知、パフォーマンス向上、および高度な
    コード/ログ分析を実行します。内部で定義されていますが、これらのコンポーネントは
    外部の期待や将来のモジュール化をサポートするために `ecosystem/memoria` ディレクトリに
    動的に書き込まれます。
4.  コードベース健全性モデリング: 数学的射影を利用して、サイクロマティック複雑度、
    テストカバレッジ、安定性などのソフトウェア品質メトリクスを定量化し、モデル化します。
5.  開発者ペルソナ適応: ユーザーのフィードバック、コンテキスト、および認識された
    緊急度に基づいて、コミュニケーションのトーンと提案の信頼度を動的に調整します。
6.  動的緊急度評価: ユーザー入力、診断キーワード、およびコードメトリクスを分析して
    問題の重要度を定量化し、システムの焦点を導きます。
7.  包括的なログ管理とメタ反省: さまざまなシステムログとAI/ユーザーフィードバックを
    取り込み、分類し、評価し、統合します。診断戦略の継続的な学習と自己改善のために
    SQLiteバックアップのカタログを使用します。
    **強調: ログファイルは削除されず、アーカイブされます。データはSQL DBに保存されます。**
8.  モジュールライフサイクル管理: 内部コンポーネントの運用メトリクス (呼び出し回数、
    成功率、レイテンシ) と健全性ステータスを追跡し、システムの健全性を監視します。
9.  自己テストと診断: 独自のコンポーネントと依存関係の機能性、アクセシビリティ、
    および整合性を検証するために、徹底的な自己診断ルーチンを実施します。
10. 運用可視性: 内部モジュールのパフォーマンスと健全性のリアルタイムで人間が読める
    コマンドラインサマリーを提供します。

使用方法:
--------------------
1.  初期化:
    `IntellisenseSystem()` のインスタンスを作成します:
    `system = IntellisenseSystem()`
    これにより、初期設定の読み込み、依存関係のチェック、およびMemoriaエコシステムコンポーネント
    (内部定義と外部ファイル生成の両方) のセットアップが自動的に処理されます。

2.  開発者入力の処理:
    AI駆動の提案と分析を得るには、`process_input` メソッドを呼び出します:
    `response = system.process_input(user_question_string, code_metrics_dictionary, user_id="optional_user_identifier")`
    - `user_question_string`: 開発者からの自然言語のクエリまたは観察。
    - `code_metrics_dictionary`: 関連するコード統計を含む辞書 (例: `{"complexity": 12.5, "coverage": 0.88, "momentum": -0.2}`).
    - `user_id`: 個別のペルソナ適応とフィードバックを追跡するためのオプションの文字列。

3.  自己診断の実行:
    システムの運用健全性と機能性を検証するには:
    `test_results = system.run_self_test()`
    結果は、各コンポーネントのステータスと推奨事項の詳細な内訳を提供します。

4.  システム健全性の監視:
    システムのモジュールとそのパフォーマンスメトリクスのリアルタイムサマリーを表示するには:
    `system.display_system_summary_grid()`

5.  設定:
    `intellisense_config.json` ファイルを編集して、システムの振る舞いをカスタマイズします。これには、
    モジュールの有効化/無効化、しきい値の調整、開発者ペルソナ特性の定義、および
    ログスキャンパスの設定が含まれます。
"""

import json
import logging
import random
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, Callable, List, Tuple
import numpy as np
import subprocess
import sys
import time
from datetime import datetime, timezone
import sqlite3
import psutil
from abc import ABC, abstractmethod
import ast
import importlib.util # 現在の構造では内部Memoria部品には使用されていませんが、将来的に外部読み込みが必要になった場合のために保持しています。
import re
import math
import traceback
import os
import shutil # moveやrmtreeなどのファイル操作のために追加

# --- グローバルロガー設定 ---
# メインシステム用に名前付きロガーを作成し、完全な制御のためにbasicConfigを避ける
logger = logging.getLogger("IntellisenseSystem")
# ロガーの全体的なレベルを設定
logger.setLevel(logging.INFO)

# これらのハンドラをグローバルに保存し、__main__で明示的に閉じる
_global_file_handler = None
_global_console_handler = None

# ハンドラが存在しない場合のみ追加する。この設定はモジュールのインポート時に一度だけ行われる
if not logger.handlers:
    # diagnostics.log用のファイルハンドラ (追記モード、"a"は累積ログにとって重要)
    _global_file_handler = logging.FileHandler('diagnostics.log', mode='a', encoding='utf-8')
    _global_file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    _global_file_handler.setFormatter(file_formatter)
    logger.addHandler(_global_file_handler)

    # コンソールハンドラ
    _global_console_handler = logging.StreamHandler()
    _global_console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    _global_console_handler.setFormatter(console_formatter)
    logger.addHandler(_global_console_handler)

def _close_all_global_handlers():
    """メインの'IntellisenseSystem'ロガーにアタッチされているすべてのハンドラをフラッシュして閉じる。"""
    global logger
    for handler in logger.handlers[:]: # リストのコピーを反復処理する
        try:
            handler.flush()
            handler.close()
            logger.removeHandler(handler)
        except Exception as e:
            # ロギングが影響を受ける可能性があるため、stderrに出力する
            print(f"[{datetime.now().isoformat()}] [ERROR] Failed to close and remove logger handler {handler}: {e}", file=sys.stderr)

# --- グローバルロガー設定終了 ---


# 依存関係インストーラー
def _get_pip_package_name(module_name: str) -> str:
  mapping = {
    'numpy': 'numpy',
    'psutil': 'psutil',
    'sentence_transformers': 'sentence-transformers',
    'pywt': 'pywavelets',
    'openai': 'openai'
  }
  return mapping.get(module_name, module_name.split('.')[0] if '.' in module_name else module_name)

def install_missing_dependencies(core_modules: List[str], optional_modules: List[str]) -> None:
  missing_critical = set()
  missing_optional = set()

  for module in core_modules:
    try:
      __import__(module)
    except ImportError:
      missing_critical.add(module)

  if missing_critical:
    logger.info("コア依存関係を確認しています...")
    for module in list(missing_critical):
      package_name = _get_pip_package_name(module)
      logger.warning(f"不足している重要な依存関係をインストールしようとしています: {package_name}")
      try:
        install_cmd = [sys.executable, "-m", "pip", "install", package_name]
        process = subprocess.Popen(install_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, stderr = process.communicate()
        if process.returncode == 0:
          logger.info(f"コアパッケージ {package_name} を正常にインストールしました。")
          try:
            __import__(module.split('.')[0] if '.' in module else module)
            missing_critical.discard(module)
          except ImportError:
            logger.error(f"{package_name} をインストールしましたが、{module} をインポートできませんでした。")
        else:
          logger.error(f"コアパッケージ {package_name} のインストールに失敗しました。エラー: {stderr}")
      except Exception as e:
        logger.error(f"{package_name} のインストール中に例外が発生しました: {e}")

  if missing_critical:
    logger.critical(f"致命的エラー: 重要な依存関係が不足しています: {', '.join(missing_critical)}。終了します。")
    sys.exit(1)

  logger.info("オプションの依存関係を確認しています...")
  for module in optional_modules:
    try:
      __import__(module)
    except ImportError:
      missing_optional.add(module)

  if missing_optional:
    for module in list(missing_optional):
      package_name = _get_pip_package_name(module)
      logger.warning(f"不足しているオプションの依存関係をインストールしようとしています: {package_name}")
      try:
        install_cmd = [sys.executable, "-m", "pip", "install", package_name]
        process = subprocess.Popen(install_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, stderr = process.communicate()
        if process.returncode == 0:
          logger.info(f"オプションパッケージ {package_name} を正常にインストールしました。")
        else:
          logger.warning(f"オプションパッケージ {package_name} のインストールに失敗しました。エラー: {stderr}")
      except Exception as e:
        logger.error(f"{package_name} のインストール中に例外が発生しました: {e}")

CORE_MODULES = ['numpy', 'psutil']
OPTIONAL_MODULES = ['sentence_transformers', 'pywt', 'openai']
install_missing_dependencies(CORE_MODULES, OPTIONAL_MODULES)

try:
  import numpy as np
except ImportError:
  np = None
  logger.warning("numpyが見つかりません。数学的モデリングと埋め込みは無効になります。")
try:
  import pywt
except ImportError:
  pywt = None
  logger.warning("pywaveletsが見つかりません。ウェーブレット解析は無効になります。")
try:
  from sentence_transformers import SentenceTransformer
except ImportError:
  SentenceTransformer = None
  logger.warning("sentence_transformersが見つかりません。ローカル埋め込み生成は無効になります。")
try:
  import psutil
except ImportError:
  psutil = None
  logger.warning("psutilが見つかりません。システムリソース監視は無効になります。")
try:
  from openai import OpenAI
except ImportError:
  OpenAI = None
  logger.warning("openaiが見つかりません。OpenAI API呼び出しは無効になります。")

class BaseEmbeddingProvider(ABC):
    """埋め込みプロバイダーの抽象基底クラス。"""
    @abstractmethod
    def get_embedding(self, text: str) -> Optional[List[float]]:
        """
        指定されたテキストの埋め込みを生成します。

        Args:
            text (str): 埋め込むテキスト。

        Returns:
            Optional[List[float]]: 埋め込みベクトル、失敗した場合はNone。
        """
        pass

class LocalEmbeddingProvider(BaseEmbeddingProvider):
    """ローカルのSentenceTransformerモデルを使用する埋め込みプロバイダー。"""
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        LocalEmbeddingProviderを初期化します。

        Args:
            model_name (str, optional): 使用するSentenceTransformerモデルの名前。
                デフォルトは "all-MiniLM-L6-v2" です。
        """
        self.model_name = model_name
        self.model: Optional[SentenceTransformer] = None
        if SentenceTransformer:
            try:
                with CaptureStdoutStderr():
                    self.model = SentenceTransformer(model_name)
                logger.info(f"LocalEmbeddingProviderがモデル '{model_name}' で初期化されました。")
            except Exception as e:
                logger.error(f"ローカル埋め込みモデル '{model_name}' の読み込みに失敗しました: {e}")
        else:
            logger.warning("LocalEmbeddingProviderはアクティブではありません。sentence_transformersライブラリが見つかりません。")

    def get_embedding(self, text: str) -> Optional[List[float]]:
        """
        ローカルモデルを使用して、指定されたテキストの埋め込みを生成します。

        Args:
            text (str): 埋め込むテキスト。

        Returns:
            Optional[List[float]]: 埋め込みベクトル、失敗した場合はNone。
        """
        if self.model is None or not text:
            logger.debug("ローカル埋め込みモデルが読み込まれていないか、テキストが空です。")
            return None
        try:
            embedding = self.model.encode(str(text), convert_to_tensor=False).tolist()
            return embedding
        except Exception as e:
            logger.error(f"テキスト '{text[:50]}...' のローカル埋め込みの取得に失敗しました: {e}")
            return None

class CaptureStdoutStderr:
  """stdoutとstderrを抑制するコンテキストマネージャー。"""
  def __enter__(self):
    self._original_stdout = sys.stdout
    self._original_stderr = sys.stderr
    sys.stdout = open(os.devnull, 'w')
    sys.stderr = open(os.devnull, 'w')
  def __exit__(self, exc_type, exc_val, exc_tb):
    sys.stdout.close()
    sys.stderr.close()
    sys.stdout = self._original_stdout
    sys.stderr = self._original_stderr

# <--- MEMORIAエコシステムクラス定義の開始 (現在は直接このファイル内) --->

# MemoriaModule (基底クラス)
class MemoriaModule(ABC):
    """すべてのMemoriaモジュールの抽象基底クラス。"""
    def __init__(self):
        """モジュールの運用メトリクスを初期化します。"""
        self._invocations = 0
        self._successful_invocations = 0
        self._total_latency = 0.0

    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> None:
        """
        指定された設定でモジュールを初期化します。

        Args:
            config (Dict[str, Any]): モジュールの設定。
        """
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """
        モジュールのヘルスチェックを実行します。

        Returns:
            bool: モジュールが正常な場合はTrue、それ以外の場合はFalse。
        """
        pass

    def _start_op(self):
        """メトリック追跡のために操作の開始をマークします。"""
        self._invocations += 1
        return time.perf_counter()

    def _end_op(self, start_time: float, success: bool = True):
        """メトリック追跡のために操作の終了をマークします。"""
        latency = time.perf_counter() - start_time
        self._total_latency += latency
        if success:
            self._successful_invocations += 1

    def get_operational_metrics(self) -> Dict[str, Any]:
        """
        モジュールの運用メトリクスを取得します。

        Returns:
            Dict[str, Any]: 運用メトリクスの辞書。
        """
        success_rate = (self._successful_invocations / self._invocations) if self._invocations > 0 else 0.0
        avg_latency_ms = (self._total_latency / self._invocations * 1000) if self._invocations > 0 else 0.0
        return {
            "invocations": self._invocations,
            "success_count": self._successful_invocations,
            "error_count": self._invocations - self._successful_invocations,
            "success_rate": round(success_rate, 4),
            "avg_latency_ms": round(avg_latency_ms, 2)
        }

# MemoriaSelfReflection
class MemoriaSelfReflection(MemoriaModule):
    """自己反省とパフォーマンス分析のためのMemoriaモジュール。"""
    def __init__(self, config: Dict[str, Any], feedback_log_path: str = 'ecosystem/memoria/feedback.jsonl'):
        """
        MemoriaSelfReflectionモジュールを初期化します。

        Args:
            config (Dict[str, Any]): モジュールの設定。
            feedback_log_path (str, optional): フィードバックログファイルのパス。
                デフォルトは 'ecosystem/memoria/feedback.jsonl' です。
        """
        super().__init__()
        self.config = config
        self.feedback_log_path = Path(feedback_log_path)
        self_reflection_config = config.get('modules', {}).get('self_reflection', {})
        self.reflection_interval = self_reflection_config.get('reflection_interval', 10)
        self.interaction_count = 0
        logger.info("MemoriaSelfReflectionが初期化されました。")

    def initialize(self, config: Dict[str, Any]) -> None:
        """
        指定された設定でモジュールを初期化します。

        Args:
            config (Dict[str, Any]): モジュールの設定。
        """
        self.config.update(config)
        self.feedback_log_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info("MemoriaSelfReflectionの初期化が完了しました。")

    def health_check(self) -> bool:
        """
        モジュールのヘルスチェックを実行します。

        Returns:
            bool: モジュールが正常な場合はTrue、それ以外の場合はFalse。
        """
        return self.feedback_log_path.parent.exists()

    def process(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        リクエストを処理し、間隔が満たされた場合に反省をトリガーします。

        Args:
            request (Dict[str, Any]): 処理するリクエスト。

        Returns:
            Dict[str, Any]: 反省プロセスの結果。
        """
        start_time = self._start_op()
        try:
            self.interaction_count += 1
            if self.interaction_count % self.reflection_interval == 0:
                result = self.reflect(request)
            else:
                result = {"status": "skipped", "message": "反省はトリガーされませんでした。"}
            self._end_op(start_time, success=True)
            return result
        except Exception as e:
            self._end_op(start_time, success=False)
            raise e

    def reflect(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        フィードバックと分析結果に基づいて反省サイクルを実行します。

        Args:
            request (Dict[str, Any]): 分析結果を含むリクエスト。

        Returns:
            Dict[str, Any]: 反省の出力。
        """
        feedback_data = self._load_feedback()
        analysis_result = request.get('analysis_result', {})
        try:
            # numpyを使用して平均を計算し、空のfeedback_dataを処理する
            avg_performance = np.mean([f.get('performance_score', 0.0) for f in feedback_data]) if feedback_data else 0.0
            optimization_suggestions = analysis_result.get('optimization_suggestions', [])
            reflection_output = {
                "status": "success",
                "avg_performance": avg_performance,
                "suggestions_applied": len(optimization_suggestions),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            if optimization_suggestions:
                self._apply_optimizations(optimization_suggestions)
            self._log_reflection(reflection_output)
            return reflection_output
        except Exception as e:
            logger.error(f"反省に失敗しました: {e}")
            return {"status": "failure", "error": str(e)}

    def _load_feedback(self) -> List[Dict[str, Any]]:
        """ログファイルからフィードバックデータを読み込みます。"""
        feedback_data = []
        if self.feedback_log_path.exists():
            with open(self.feedback_log_path, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        feedback_data.append(json.loads(line.strip()))
                    except json.JSONDecodeError:
                        logger.warning(f"フィードバックログの不正なJSON行をスキップします: {line.strip()[:100]}...")
                        continue
        return feedback_data

    def _apply_optimizations(self, suggestions: List[str]):
        """提案に基づいて最適化を適用します。"""
        for suggestion in suggestions:
            if "increase_reflection_interval" in suggestion:
                if 'modules' not in self.config: self.config['modules'] = {}
                if 'self_reflection' not in self.config['modules']: self.config['modules']['self_reflection'] = {}
                self.config['modules']['self_reflection']['reflection_interval'] = \
                    self.config['modules']['self_reflection'].get('reflection_interval', 10) + 5
                logger.info("最適化の提案に基づいて反省間隔を増やしました。")

    def _log_reflection(self, reflection_output: Dict[str, Any]):
        """反省サイクルの出力をログに記録します。"""
        with open(self.feedback_log_path, 'a', encoding='utf-8') as f:
            json.dump(reflection_output, f)
            f.write('\n')
        logger.info("反省出力をログに記録しました。")

# MemoriaOptimizationEngine
class MemoriaOptimizationEngine(MemoriaModule):
    """パフォーマンスに基づいてシステムパラメータを最適化するためのMemoriaモジュール。"""
    def __init__(self, config: Dict[str, Any]):
        """
        MemoriaOptimizationEngineを初期化します。

        Args:
            config (Dict[str, Any]): モジュールの設定。
        """
        super().__init__()
        self.config = config
        self.optimization_threshold = config.get('modules', {}).get('optimization_engine', {}).get('optimization_threshold', 0.8)
        logger.info("MemoriaOptimizationEngineが初期化されました。")

    def initialize(self, config: Dict[str, Any]) -> None:
        """
        指定された設定でモジュールを初期化します。

        Args:
            config (Dict[str, Any]): モジュールの設定。
        """
        self.config.update(config)
        logger.info("MemoriaOptimizationEngineの初期化が完了しました。")

    def health_check(self) -> bool:
        """
        モジュールのヘルスチェックを実行します。

        Returns:
            bool: モジュールが正常な場合はTrue、それ以外の場合はFalse。
        """
        return True

    def process(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        リクエストを処理し、パフォーマンスがしきい値を下回る場合に最適化をトリガーします。

        Args:
            request (Dict[str, Any]): 処理するリクエスト。

        Returns:
            Dict[str, Any]: 最適化プロセスの結果。
        """
        start_time = self._start_op()
        try:
            analysis_result = request.get('analysis_result', {})
            performance_score = analysis_result.get('performance_score', 0.0)
            if performance_score < self.optimization_threshold:
                result = self.optimize(analysis_result)
            else:
                result = {"status": "skipped", "message": "パフォーマンスがしきい値を超えています。"}
            self._end_op(start_time, success=True)
            return result
        except Exception as e:
            self._end_op(start_time, success=False)
            raise e

    def optimize(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析結果に基づいて最適化を実行します。

        Args:
            analysis_result (Dict[str, Any]): 最適化の基礎となる分析結果。

        Returns:
            Dict[str, Any]: 最適化の出力。
        """
        try:
            suggestions = analysis_result.get('optimization_suggestions', [])
            if not suggestions:
                return {"status": "success", "message": "最適化は必要ありません。"}

            for suggestion in suggestions:
                if "adjust_confidence" in suggestion:
                    if 'modules' not in self.config: self.config['modules'] = {}
                    if 'self_reflection' not in self.config['modules']: self.config['modules']['self_reflection'] = {}
                    self.config['modules']['self_reflection']['confidence_level'] = min(
                        1.0, self.config['modules']['self_reflection'].get('confidence_level', 0.7) + 0.1
                    )
                    logger.info("最適化の提案に基づいてself_reflectionの信頼度を調整しました。")

            logger.info(f"{len(suggestions)}件の最適化を適用しました。")
            return {"status": "success", "optimizations_applied": len(suggestions)}
        except Exception as e:
            logger.error(f"最適化に失敗しました: {e}")
            return {"status": "failure", "error": str(e)}

# MemoriaAnalysisInterface
class MemoriaAnalysisInterface(MemoriaModule):
    """外部分析API (例: OpenAI) とのインターフェースをとるためのMemoriaモジュール。"""
    def __init__(self, config: Dict[str, Any]):
        """
        MemoriaAnalysisInterfaceを初期化します。

        Args:
            config (Dict[str, Any]): モジュールの設定。
        """
        super().__init__()
        self.config = config
        self.client = None
        self.api_enabled = config.get('modules', {}).get('analysis_interface', {}).get('enabled', False)
        if OpenAI and self.api_enabled:
            try:
                self.client = OpenAI(api_key="mock-api-key")
                logger.info("MemoriaAnalysisInterface OpenAIクライアントが初期化されました。")
            except Exception as e:
                logger.error(f"MemoriaAnalysisInterface OpenAIクライアントの初期化に失敗しました: {e}")
        logger.info("MemoriaAnalysisInterfaceが初期化されました。")

    def initialize(self, config: Dict[str, Any]) -> None:
        """
        指定された設定でモジュールを初期化します。

        Args:
            config (Dict[str, Any]): モジュールの設定。
        """
        self.config.update(config)
        self.api_enabled = config.get('modules', {}).get('analysis_interface', {}).get('enabled', False)
        if OpenAI and self.api_enabled and not self.client:
            try:
                self.client = OpenAI(api_key="mock-api-key")
                logger.info("設定更新時にMemoriaAnalysisInterface OpenAIクライアントが再初期化されました。")
            except Exception as e:
                logger.error(f"MemoriaAnalysisInterface OpenAIクライアントの再初期化に失敗しました: {e}")
        elif not self.api_enabled and self.client:
            self.client = None
        logger.info("MemoriaAnalysisInterfaceの初期化が完了しました。")

    def health_check(self) -> bool:
        """
        モジュールのヘルスチェックを実行します。

        Returns:
            bool: モジュールが正常な場合はTrue、それ以外の場合はFalse。
        """
        return self.client is not None or not self.api_enabled

    def process(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        リクエストを外部分析APIに送信して処理します。

        Args:
            request (Dict[str, Any]): 処理するリクエスト。

        Returns:
            Dict[str, Any]: 分析APIからの結果。
        """
        start_time = self._start_op()
        try:
            if not self.api_enabled or not self.client:
                result = {"status": "skipped", "message": "OpenAI APIが有効でないか、クライアントが初期化されていません。"}
            else:
                code_snippet = request.get('code_snippet', '')
                performance_metrics = request.get('performance_metrics', {})
                prompt = (f"以下のPythonコードとシステムパフォーマンスメトリクスを分析してください...")

                response = {
                    "performance_score": 0.85,
                    "optimization_suggestions": ["ネストしたループを減らす", "明確にするために型ヒントを追加する"]
                }
                logger.info(f"MemoriaAnalysisInterface OpenAI分析が完了しました: スコア {response['performance_score']}")
                result = {"status": "success", "analysis_result": response}
            self._end_op(start_time, success=result['status'] == 'success')
            return result
        except Exception as e:
            self._end_op(start_time, success=False)
            raise e

# MemoriaCore - このクラスは他のMemoriaクラスを認識する必要があります
# これらは現在、この同じファイルの前の方で定義されています。
class MemoriaCore(MemoriaModule):
    """Memoriaエコシステムのコアであり、他のすべてのMemoriaモジュールを管理します。"""
    def __init__(self, config_path: str = 'ecosystem/memoria/config/memoria_config.json'):
        """
        MemoriaCoreを初期化します。

        Args:
            config_path (str, optional): Memoria設定ファイルへのパス。
                デフォルトは 'ecosystem/memoria/config/memoria_config.json' です。
        """
        super().__init__()
        self.config_path = Path(config_path)
        self.config = {}
        self.modules: Dict[str, MemoriaModule] = {}
        self.load_config()
        logger.info("MemoriaCoreが初期化されました。")

    def load_config(self):
        """ディスクからMemoria設定を読み込みます。"""
        if not self.config_path.exists():
            self._create_default_config()
        with open(self.config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        logger.info("MemoriaCore設定が読み込まれました。")

    def _create_default_config(self):
        """デフォルトのMemoria設定ファイルを作成します。"""
        default_config = {
            "modules": {
                "self_reflection": {"enabled": True, "reflection_interval": 10},
                "optimization_engine": {"enabled": True, "optimization_threshold": 0.8},
                "analysis_interface": {"enabled": True, "api_provider": "openai"}
            },
            "system_parameters": {
                "log_level": "INFO",
                "max_retries": 3,
                "analysis_timeout": 30.0
            }
        }
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=2)
        logger.info(f"デフォルトのmemoria_config.jsonを {self.config_path} に作成しました")

    def save_config(self):
        """現在のMemoria設定をディスクに保存します。"""
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=2)
        logger.info("MemoriaCore設定が保存されました。")

    def initialize(self, config: Dict[str, Any]) -> None:
        """
        MemoriaCoreとそのサブモジュールを初期化します。

        Args:
            config (Dict[str, Any]): モジュールの設定。
        """
        self.config.update(config)
        self.save_config()
        for module_name, module_config in self.config.get('modules', {}).items():
            if module_config.get('enabled', False):
                logger.info(f"モジュールを初期化しています: {module_name}")
                if module_name == "self_reflection":
                    self.modules[module_name] = MemoriaSelfReflection(self.config)
                elif module_name == "optimization_engine":
                    self.modules[module_name] = MemoriaOptimizationEngine(self.config)
                elif module_name == "analysis_interface":
                    self.modules[module_name] = MemoriaAnalysisInterface(self.config)

                if hasattr(self.modules[module_name], 'initialize') and callable(self.modules[module_name].initialize):
                    self.modules[module_name].initialize(module_config)
        logger.info("MemoriaCoreの初期化が完了しました。")

    def register_module(self, name: str, module: MemoriaModule):
        """
        新しいMemoriaモジュールをコアに登録します。

        Args:
            name (str): モジュールの名前。
            module (MemoriaModule): 登録するモジュールインスタンス。
        """
        self.modules[name] = module
        logger.info(f"登録されたモジュール: {name}")

    def health_check(self) -> bool:
        """
        MemoriaCoreとすべてのサブモジュールのヘルスチェックを実行します。

        Returns:
            bool: すべてのモジュールが正常な場合はTrue、それ以外の場合はFalse。
        """
        return all(module.health_check() for module in self.modules.values())

    def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        リクエストをすべての登録済みMemoriaモジュールに渡して処理します。

        Args:
            request (Dict[str, Any]): 処理するリクエスト。

        Returns:
            Dict[str, Any]: すべてのモジュールからの集約された結果。
        """
        start_time = self._start_op()
        result = {"status": "success", "data": {}}
        success = True
        for name, module in self.modules.items():
            op_start_time = module._start_op()
            try:
                if hasattr(module, 'process') and callable(module.process):
                    module_result = module.process(request)
                    result["data"][name] = module_result
                    module._end_op(op_start_time, success=True)
                else:
                    logger.warning(f"モジュール {name} には 'process' メソッドがありません。")
                    result["data"][name] = {"error": "No process method"}
                    module._end_op(op_start_time, success=False)
            except Exception as e:
                logger.error(f"モジュール {name} の処理中に失敗しました: {e}")
                result["status"] = "partial_failure"
                result["data"][name] = {"error": str(e)}
                success = False
                module._end_op(op_start_time, success=False)
        self._end_op(start_time, success=success)
        return result

# <--- MEMORIAエコシステムクラス定義の終了 --->


class SystemDiagnostics:
  """システムコンポーネントの検証とテスト、およびファイル作成を処理します。"""
  def __init__(self, bootstrapper: 'IntellisenseBootstrapper'):
    """
    SystemDiagnosticsコンポーネントを初期化します。

    Args:
        bootstrapper (IntellisenseBootstrapper): ブートストラッパーのインスタンス。
    """
    self.bootstrapper = bootstrapper
    self.diagnostic_log_path = Path("diagnostics.log")
    logger.info("SystemDiagnosticsが初期化されました。")

  def verify_file_creation(self, file_path: Path) -> bool:
    """
    ファイルが存在し、構文的に有効であるかを確認します。

    Args:
        file_path (Path): 検証するファイルへのパス。

    Returns:
        bool: ファイルが有効な場合はTrue、それ以外の場合はFalse。
    """
    if not file_path.exists():
      logger.error(f"ファイル {file_path} が存在しません。")
      return False
    if file_path.suffix == '.py':
      try:
        with open(file_path, 'r', encoding='utf-8') as f:
          ast.parse(f.read())
        logger.info(f"ファイル {file_path} は構文的に有効です。")
        return True
      except SyntaxError as e:
        logger.error(f"{file_path} の構文エラー: {e}")
        return False
    elif file_path.suffix == '.json':
      try:
        with open(file_path, 'r', encoding='utf-8') as f:
          json.load(f)
        logger.info(f"ファイル {file_path} は有効なJSONです。")
        return True
      except json.JSONDecodeError as e:
        logger.error(f"{file_path} の無効なJSON: {e}")
        return False
    logger.info(f"ファイル {file_path} は存在し、フォーマットは特にチェックされていません。")
    return True

  def verify_module_import(self, module_path: Path, module_name: str) -> bool:
    """
    指定されたパスからモジュールをインポートできるかを確認します。

    Args:
        module_path (Path): Pythonモジュールファイルへのパス。
        module_name (str): モジュールとしてインポートする名前。

    Returns:
        bool: モジュールがインポートできる場合はTrue、それ以外の場合はFalse。
    """
    try:
      project_root = module_path.parents[2]
      original_sys_path = sys.path[:]
      if str(project_root) not in sys.path:
          sys.path.insert(0, str(project_root))

      spec = importlib.util.spec_from_file_location(module_name, module_path)
      if spec is None or spec.loader is None:
        logger.error(f"{module_path} のモジュール仕様を作成できません")
        return False
      module = importlib.util.module_from_spec(spec)
      sys.modules[module_name] = module
      spec.loader.exec_module(module)
      logger.info(f"モジュール {module_name} が {module_path} から正常にインポートされました。")
      return True
    except Exception as e:
      logger.error(f"モジュール {module_name} を {module_path} からインポートできませんでした: {e}")
      return False
    finally:
        sys.path = original_sys_path


  def run_diagnostics(self, files_to_verify: List[Path], modules_to_verify: List[Tuple[Path, str]]) -> Dict[str, bool]:
    """
    ファイルとモジュールのリストに対して診断を実行します。

    Args:
        files_to_verify (List[Path]): 検証するファイルパスのリスト。
        modules_to_verify (List[Tuple[Path, str]]): 各タプルが
            モジュールへのパスとそのインポート名を含むタプルのリスト。

    Returns:
        Dict[str, bool]: 診断結果の辞書。
    """
    results = {}
    for file_path in files_to_verify:
      results[str(file_path)] = self.verify_file_creation(file_path)
    for file_path, module_name in modules_to_verify:
      results[f"module_{module_name}"] = self.verify_module_import(file_path, module_name)
    logger.info(f"診断結果: {json.dumps(results, indent=2)}")
    return results


# Memoriaエコシステムファイル用のコンテンツ文字列 (現在はローカルクラス定義で冗長ですが、
# ユーザーの要求に従ってファイル生成ロジックのために保持されています)。
# これらは、*生成されたファイルコンテキスト*の相対インポートを含まなければなりません。

MEMORIA_MODULE_BASE_CONTENT = """
import logging
from abc import ABC, abstractmethod
import time
from typing import Dict, Any

logger = logging.getLogger(__name__)

class MemoriaModule(ABC):
  def __init__(self):
    self._invocations = 0
    self._successful_invocations = 0
    self._total_latency = 0.0

  @abstractmethod
  def initialize(self, config: Dict[str, Any]) -> None:
    pass

  @abstractmethod
  def health_check(self) -> bool:
    pass

  def _start_op(self):
    self._invocations += 1
    return time.perf_counter()

  def _end_op(self, start_time: float, success: bool = True):
    latency = time.perf_counter() - start_time
    self._total_latency += latency
    if success:
      self._successful_invocations += 1

  def get_operational_metrics(self) -> Dict[str, Any]:
    success_rate = (self._successful_invocations / self._invocations) if self._invocations > 0 else 0.0
    avg_latency_ms = (self._total_latency / self._invocations * 1000) if self._invocations > 0 else 0.0
    return {
      "invocations": self._invocations,
      "success_count": self._successful_invocations,
      "error_count": self._invocations - self._successful_invocations,
      "success_rate": round(success_rate, 4),
      "avg_latency_ms": round(avg_latency_ms, 2)
    }
"""

MEMORIA_CORE_CONTENT = """
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
import time

# それぞれのファイルからMemoriaサブモジュールをインポートする
from .memoria_module import MemoriaModule
from .self_reflection import MemoriaSelfReflection
from .optimization_engine import MemoriaOptimizationEngine
from .analysis_interface import MemoriaAnalysisInterface

logger = logging.getLogger(__name__)

class MemoriaCore(MemoriaModule):
  def __init__(self, config_path: str = 'ecosystem/memoria/config/memoria_config.json'):
    super().__init__()
    self.config_path = Path(config_path)
    self.config = {}
    self.modules: Dict[str, MemoriaModule] = {}
    self.load_config()
    logger.info("MemoriaCore initialized.")

  def load_config(self):
    if not self.config_path.exists():
      self._create_default_config()
    with open(self.config_path, 'r', encoding='utf-8') as f:
      self.config = json.load(f)
    logger.info("MemoriaCore configuration loaded.")

  def _create_default_config(self):
    default_config = {
      "modules": {
        "self_reflection": {"enabled": True, "reflection_interval": 10},
        "optimization_engine": {"enabled": True, "optimization_threshold": 0.8},
        "analysis_interface": {"enabled": True, "api_provider": "openai"}
      },
      "system_parameters": {
        "log_level": "INFO",
        "max_retries": 3,
        "analysis_timeout": 30.0
      }
    }
    self.config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(self.config_path, 'w', encoding='utf-8') as f:
      json.dump(default_config, f, indent=2)
    logger.info(f"Created default memoria_config.json at {self.config_path}")

  def save_config(self):
    with open(self.config_path, 'w', encoding='utf-8') as f:
      json.dump(self.config, f, indent=2)
    logger.info("MemoriaCore configuration saved.")

  def initialize(self, config: Dict[str, Any]) -> None:
    self.config.update(config)
    self.save_config()
    for module_name, module_config in self.config.get('modules', {}).items():
      if module_config.get('enabled', False):
        logger.info(f"Initializing module: {module_name}")
        if module_name == "self_reflection":
          self.modules[module_name] = MemoriaSelfReflection(self.config)
        elif module_name == "optimization_engine":
          self.modules[module_name] = MemoriaOptimizationEngine(self.config)
        elif module_name == "analysis_interface":
          self.modules[module_name] = MemoriaAnalysisInterface(self.config)

        if hasattr(self.modules[module_name], 'initialize') and callable(self.modules[module_name].initialize):
            self.modules[module_name].initialize(module_config)
    logger.info("MemoriaCore initialization complete.")

  def register_module(self, name: str, module: 'MemoriaModule'):
    self.modules[name] = module
    logger.info(f"Registered module: {name}")

  def health_check(self) -> bool:
    return all(module.health_check() for module in self.modules.values())

  def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
    start_time = self._start_op()
    result = {"status": "success", "data": {}}
    success = True
    for name, module in self.modules.items():
      op_start_time = module._start_op()
      try:
        if hasattr(module, 'process') and callable(module.process):
          module_result = module.process(request)
          result["data"][name] = module_result
          module._end_op(op_start_time, success=True)
        else:
            logger.warning(f"Module {name} does not have a 'process' method.")
            result["data"][name] = {"error": "No process method"}
            module._end_op(op_start_time, success=False)
      except Exception as e:
        logger.error(f"Module {name} failed during processing: {e}")
        result["status"] = "partial_failure"
        result["data"][name] = {"error": str(e)}
        success = False
        module._end_op(op_start_time, success=False)
    self._end_op(start_time, success=success)
    return result
"""

SELF_REFLECTION_CONTENT = """
import json
import logging
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime, timezone
import numpy as np
import time

from .memoria_module import MemoriaModule

logger = logging.getLogger(__name__)

class MemoriaSelfReflection(MemoriaModule):
  def __init__(self, config: Dict[str, Any], feedback_log_path: str = 'ecosystem/memoria/feedback.jsonl'):
    super().__init__()
    self.config = config
    self.feedback_log_path = Path(feedback_log_path)
    self_reflection_config = config.get('modules', {}).get('self_reflection', {})
    self.reflection_interval = self_reflection_config.get('reflection_interval', 10)
    self.interaction_count = 0
    logger.info("MemoriaSelfReflection initialized.")

  def initialize(self, config: Dict[str, Any]) -> None:
    self.config.update(config)
    self.feedback_log_path.parent.mkdir(parents=True, exist_ok=True)
    logger.info("MemoriaSelfReflection initialization complete.")

  def health_check(self) -> bool:
    return self.feedback_log_path.parent.exists()

  def process(self, request: Dict[str, Any]) -> Dict[str, Any]:
    start_time = self._start_op()
    try:
      self.interaction_count += 1
      if self.interaction_count % self.reflection_interval == 0:
        result = self.reflect(request)
      else:
        result = {"status": "skipped", "message": "Reflection not triggered."}
      self._end_op(start_time, success=True)
      return result
    except Exception as e:
      self._end_op(start_time, success=False)
      raise e

  def reflect(self, request: Dict[str, Any]) -> Dict[str, Any]:
    feedback_data = self._load_feedback()
    analysis_result = request.get('analysis_result', {})
    try:
      avg_performance = np.mean([f.get('performance_score', 0.0) for f in feedback_data]) if feedback_data else 0.0
      optimization_suggestions = analysis_result.get('optimization_suggestions', [])
      reflection_output = {
        "status": "success",
        "avg_performance": avg_performance,
        "suggestions_applied": len(optimization_suggestions),
        "timestamp": datetime.now(timezone.utc).isoformat()
      }
      if optimization_suggestions:
        self._apply_optimizations(optimization_suggestions)
      self._log_reflection(reflection_output)
      return reflection_output
    except Exception as e:
      logger.error(f"Reflection failed: {e}")
      return {"status": "failure", "error": str(e)}

  def _load_feedback(self) -> List[Dict[str, Any]]:
    feedback_data = []
    if self.feedback_log_path.exists():
      with open(self.feedback_log_path, 'r', encoding='utf-8') as f:
        for line in f:
          try:
            feedback_data.append(json.loads(line.strip()))
          except json.JSONDecodeError:
            logger.warning(f"Skipping malformed JSON line in feedback log: {line.strip()[:100]}...")
            continue
    return feedback_data

  def _apply_optimizations(self, suggestions: List[str]):
    for suggestion in suggestions:
      if "increase_reflection_interval" in suggestion:
        if 'modules' not in self.config: self.config['modules'] = {}
        if 'self_reflection' not in self.config['modules']: self.config['modules']['self_reflection'] = {}
        self.config['modules']['self_reflection']['reflection_interval'] = \\
          self.config['modules']['self_reflection'].get('reflection_interval', 10) + 5
        logger.info("Increased reflection interval based on optimization suggestion.")

  def _log_reflection(self, reflection_output: Dict[str, Any]):
    with open(self.feedback_log_path, 'a', encoding='utf-8') as f:
      json.dump(reflection_output, f)
      f.write('\\n')
    logger.info("Logged reflection output.")
"""

OPTIMIZATION_ENGINE_CONTENT = """
import logging
from typing import Dict, Any
import time

from .memoria_module import MemoriaModule

logger = logging.getLogger(__name__)

class MemoriaOptimizationEngine(MemoriaModule):
  def __init__(self, config: Dict[str, Any]):
    super().__init__()
    self.config = config
    self.optimization_threshold = config.get('modules', {}).get('optimization_engine', {}).get('optimization_threshold', 0.8)
    logger.info("MemoriaOptimizationEngine initialized.")

  def initialize(self, config: Dict[str, Any]) -> None:
    self.config.update(config)
    logger.info("MemoriaOptimizationEngine initialization complete.")

  def health_check(self) -> bool:
    return True

  def process(self, request: Dict[str, Any]) -> Dict[str, Any]:
    start_time = self._start_op()
    try:
      analysis_result = request.get('analysis_result', {})
      performance_score = analysis_result.get('performance_score', 0.0)
      if performance_score < self.optimization_threshold:
        result = self.optimize(analysis_result)
      else:
        result = {"status": "skipped", "message": "Performance above threshold."}
      self._end_op(start_time, success=True)
      return result
    except Exception as e:
      self._end_op(start_time, success=False)
      raise e

  def optimize(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
    try:
      suggestions = analysis_result.get('optimization_suggestions', [])
      if not suggestions:
        return {"status": "success", "message": "No optimizations needed."}

      for suggestion in suggestions:
        if "adjust_confidence" in suggestion:
          if 'modules' not in self.config: self.config['modules'] = {}
          if 'self_reflection' not in self.config['modules']: self.config['modules']['self_reflection'] = {}
          self.config['modules']['self_reflection']['confidence_level'] = min(
            1.0, self.config['modules']['self_reflection'].get('confidence_level', 0.7) + 0.1
          )
          logger.info("Adjusted self_reflection confidence based on optimization suggestion.")

      logger.info(f"Applied {len(suggestions)} optimizations.")
      return {"status": "success", "optimizations_applied": len(suggestions)}
    except Exception as e:
      logger.error(f"Optimization failed: {e}")
      return {"status": "failure", "error": str(e)}
"""

ANALYSIS_INTERFACE_CONTENT = """
import logging
from typing import Dict, Any
import time

try:
  from openai import OpenAI
except ImportError:
  OpenAI = None
  logging.warning("OpenAI not found. AI Analysis Interface will be limited.")

from .memoria_module import MemoriaModule

logger = logging.getLogger(__name__)

class MemoriaAnalysisInterface(MemoriaModule):
  def __init__(self, config: Dict[str, Any]):
    super().__init__()
    self.config = config
    self.client = None
    self.api_enabled = config.get('modules', {}).get('analysis_interface', {}).get('enabled', False)
    if OpenAI and self.api_enabled:
      try:
        self.client = OpenAI(api_key="mock-api-key")
        logger.info("MemoriaAnalysisInterface OpenAI client initialized.")
      except Exception as e:
        logger.error(f"Failed to initialize MemoriaAnalysisInterface OpenAI client: {e}")
    logger.info("MemoriaAnalysisInterface initialized.")

  def initialize(self, config: Dict[str, Any]) -> None:
    self.config.update(config)
    self.api_enabled = config.get('modules', {}).get('analysis_interface', {}).get('enabled', False)
    if OpenAI and self.api_enabled and not self.client:
      try:
        self.client = OpenAI(api_key="mock-api-key")
        logger.info("MemoriaAnalysisInterface OpenAI client re-initialized upon configuration update.")
      except Exception as e:
        logger.error(f"Failed to re-initialize MemoriaAnalysisInterface OpenAI client: {e}")
    elif not self.api_enabled and self.client:
      self.client = None
    logger.info("MemoriaAnalysisInterface initialization complete.")

  def health_check(self) -> bool:
    return self.client is not None or not self.api_enabled

  def process(self, request: Dict[str, Any]) -> Dict[str, Any]:
    start_time = self._start_op()
    try:
      if not self.api_enabled or not self.client:
        result = {"status": "skipped", "message": "OpenAI API not enabled or client not initialized."}
      else:
        code_snippet = request.get('code_snippet', '')
        performance_metrics = request.get('performance_metrics', {})
        prompt = (f"Analyze the following Python code and system performance metrics...")

        response = {
          "performance_score": 0.85,
          "optimization_suggestions": ["Reduce nested loops", "Add type hints for clarity"]
        }
        logger.info(f"MemoriaAnalysisInterface OpenAI analysis completed: Score {response['performance_score']}")
        result = {"status": "success", "analysis_result": response}
      self._end_op(start_time, success=result['status'] == 'success')
      return result
    except Exception as e:
      self._end_op(start_time, success=False)
      raise e
"""


class IntellisenseBootstrapper:
  """IntellisenseSystemとMemoriaエコシステムの構成と初期化を管理します。"""
  def __init__(self, config_path: str = 'intellisense_config.json'):
    """
    IntellisenseBootstrapperを初期化します。

    Args:
        config_path (str, optional): メイン設定ファイルへのパス。
            デフォルトは 'intellisense_config.json' です。
    """
    self.config_path = Path(config_path)
    self.config = {}
    self.embedding_dimension = 384
    self.memoria_ecosystem_path = Path('ecosystem/memoria')
    self.embedding_provider = LocalEmbeddingProvider()
    self.diagnostics = SystemDiagnostics(self)
    self.load_config()
    self.initialize_memoria_ecosystem() # Memoriaファイルが外部で使用される前に作成/更新されることを保証します
    self.verify_memoria_ecosystem() # 外部で作成されたファイルを検証します

  def load_config(self):
    """メイン設定ファイルを読み込みます。存在しない場合はデフォルトを作成します。"""
    if not self.config_path.exists():
      self._create_default_config()
    with open(self.config_path, 'r', encoding='utf-8') as f:
      self.config = json.load(f)
    logger.info("IntellisenseSystem設定が読み込まれました。")

    if self.embedding_provider.model:
      try:
        test_embedding = self.embedding_provider.get_embedding("test_string")
        if test_embedding:
          self.config['embedding_dimension'] = len(test_embedding)
          self.save_config()
        else:
          logger.warning("プロバイダーからテスト埋め込みを取得できませんでした。デフォルトのembedding_dimensionを使用します。")
      except Exception as e:
        logger.warning(f"プロバイダーからの埋め込み次元の決定中にエラーが発生しました: {e}。設定済みまたはデフォルトを使用します。")

  def _create_default_config(self):
    """デフォルトの設定ファイルを作成します。"""
    default_config = {
      "core_directives": [
        {"name": "code_quality", "weight": 15},
        {"name": "performance_optimization", "weight": 10},
        {"name": "security", "weight": 10}
      ],
      "parameters": {
        "complexity_threshold": {"value": 10.0},
        "coverage_target": {"value": 0.85},
        "stability_factor": {"value": 1.0}
      },
      "developer_persona": {
        "tone": "collaborative",
        "confidence_level": 0.7,
        "urgency_level": 0.5
      },
      "diagnostic_keywords": {
        "critical": ["error", "failure", "crash", "urgent"],
        "warning": ["warning", "issue", "bug"],
        "info": ["info", "suggestion", "improvement"]
      },
      "meta_reflection": {
        "reflection_interval": 10,
        "feedback_log_path": "ai_suggestion_feedback.jsonl",
        "log_reflector_interval_sec": 600,
        "log_reflector_window_lines": 50
      },
      "embedding_dimension": 384,
      "wavelet_enabled": True,
      "system_monitoring": {
        "cpu_threshold": 80.0,
        "memory_threshold": 80.0
      },
      "memoria_ecosystem": {
        "enabled": True,
        "config_path": "ecosystem/memoria/config/memoria_config.json"
      },
      "log_management": {
        "enabled": True,
        "scan_paths": [
          "logs/",
          "diagnostics.log", # 現在の実行のログデータを動的にスキャンするために含まれています
          "ecosystem/memoria/feedback.jsonl",
          "logs/intellisense_data_synthesis_report.log",
          "logs/intellisense_self_test_report.jsonl"
        ],
        "scan_interval_sec": 300,
        "assessment_threshold_ai_learning": 0.7,
        "log_entry_patterns": {
          "jsonl_timestamp": r"^\s*\{\s*\"timestamp\":\s*\"([^\"]+)\".*\"level\":\s*\"([^\"]+)\".*\"message\":\s*\"([^\"]+)\".*\}",
          "simple_log": r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(?:,\d{3})?) - (\w+) - (.*)", # 修正された正規表現エスケープ
          "feedback": r".*feedback.*",
        },
        "advanced_parsers": [
          {
            "name": "performance_metrics",
            "regex": [
              r"CPU: (?P<cpu_usage>\d+\.\d+)%, Memory: (?P<memory_usage>\d+\.\d+)%", # 修正された正規表現エスケープ
              r"Latency: (?P<latency_ms>\d+\.\d+)ms" # 修正された正規表現エスケープ
            ],
            "context_category": "system_performance"
          },
          {
            "name": "database_errors",
            "regex": [
              r"Failed to connect to database (?P<db_name>[a-zA-Z0-9_]+)\." # 修正された正規表現エスケープ
            ],
            "context_category": "database_connection_issue"
          },
          {
            "name": "module_errors",
            "regex": [
              r"Module (?P<module_name>[a-zA-Z_]+) failed: (?P<error_message>.*)"
            ],
            "context_category": "module_runtime_error"
          },
           {
            "name": "test_results",
            "regex": [
              r"Tests run: (?P<total_tests>\d+), Failures: (?P<failed_tests>\d+), Errors: (?P<error_tests>\d+)" # 修正された正規表現エスケープ
            ],
            "context_category": "testing_summary"
          },
          { # 新規: 自己テストレポート分析
            "name": "self_test_summary",
            "regex": [
              r"\{\"timestamp\":\s*\"(?P<test_timestamp>[^\"]+)\",\s*\"overall_status\":\s*\"(?P<overall_status>[^\"]+)\",.*\"message\":\s*\"(?P<test_message>[^\"]+)\",\s*\"severity\":\s*\"(?P<test_severity>[^\"]+)\"" # 修正された正規表現エスケープ
            ],
            "context_category": "intellisense_self_test"
          }
        ]
      },
      # 新規: モジュール追跡設定
      "module_tracking": {
        "enabled": True,
        "tracking_interval_sec": 60 # ModuleOrchestratorがスナップショットを記録する頻度
      }
    }
    with open(self.config_path, 'w', encoding='utf-8') as f:
      json.dump(default_config, f, indent=2)
    logger.info(f"デフォルトのintellisense_config.jsonを {self.config_path} に作成しました")

  def save_config(self):
    """現在の設定をディスクに保存します。"""
    with open(self.config_path, 'w', encoding='utf-8') as f:
      json.dump(self.config, f, indent=2)
    logger.info("設定が保存されました。")

  def initialize_memoria_ecosystem(self):
    """Memoriaエコシステムを初期化し、ファイルが見つからないか古い場合は生成します。"""
    if not self.config.get('memoria_ecosystem', {}).get('enabled', False):
      logger.info("設定でMemoriaエコシステムが無効になっています。")
      return

    self.memoria_ecosystem_path.mkdir(parents=True, exist_ok=True)

    memoria_files = {
      self.memoria_ecosystem_path / '__init__.py': """
from .memoria_core import MemoriaCore
from .memoria_module import MemoriaModule
from .self_reflection import MemoriaSelfReflection
from .optimization_engine import MemoriaOptimizationEngine
from .analysis_interface import MemoriaAnalysisInterface
""",
      self.memoria_ecosystem_path / 'memoria_module.py': MEMORIA_MODULE_BASE_CONTENT,
      self.memoria_ecosystem_path / 'memoria_core.py': MEMORIA_CORE_CONTENT,
      self.memoria_ecosystem_path / 'self_reflection.py': SELF_REFLECTION_CONTENT,
      self.memoria_ecosystem_path / 'optimization_engine.py': OPTIMIZATION_ENGINE_CONTENT,
      self.memoria_ecosystem_path / 'analysis_interface.py': ANALYSIS_INTERFACE_CONTENT,
      self.memoria_ecosystem_path / 'config' / 'memoria_config.json': json.dumps({
          "modules": {
              "self_reflection": {"enabled": True, "reflection_interval": 10},
              "optimization_engine": {"enabled": True, "optimization_threshold": 0.8},
              "analysis_interface": {"enabled": True, "api_provider": "openai"}
          },
          "system_parameters": {
              "log_level": "INFO",
              "max_retries": 3,
              "analysis_timeout": 30.0
          }
      }, indent=2)
    }

    for file_path, content in memoria_files.items():
      current_content_bytes = None
      if file_path.exists():
          with open(file_path, 'rb') as f:
              current_content_bytes = f.read()

      new_content_bytes = content.encode('utf-8')

      if not file_path.exists() or current_content_bytes != new_content_bytes:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
          f.write(content)
        logger.info(f"Memoriaエコシステムファイルを生成/更新しました: {file_path}")
      else:
        logger.info(f"Memoriaエコシステムファイルは既に存在し、最新です: {file_path}")


  def verify_memoria_ecosystem(self):
    """Memoriaエコシステムファイルの作成と整合性を検証します。"""
    if not self.config.get('memoria_ecosystem', {}).get('enabled', False):
      logger.info("Memoriaエコシステムが無効なため、検証をスキップします。")
      return

    files_to_verify = [
      self.memoria_ecosystem_path / '__init__.py',
      self.memoria_ecosystem_path / 'memoria_module.py',
      self.memoria_ecosystem_path / 'memoria_core.py',
      self.memoria_ecosystem_path / 'self_reflection.py',
      self.memoria_ecosystem_path / 'optimization_engine.py',
      self.memoria_ecosystem_path / 'analysis_interface.py',
      self.memoria_ecosystem_path / 'config' / 'memoria_config.json'
    ]
    modules_to_verify = [
      (self.memoria_ecosystem_path / 'memoria_module.py', 'ecosystem.memoria.memoria_module'),
      (self.memoria_ecosystem_path / 'memoria_core.py', 'ecosystem.memoria.memoria_core'),
      (self.memoria_ecosystem_path / 'self_reflection.py', 'ecosystem.memoria.self_reflection'),
      (self.memoria_ecosystem_path / 'optimization_engine.py', 'ecosystem.memoria.optimization_engine'),
      (self.memoria_ecosystem_path / 'analysis_interface.py', 'ecosystem.memoria.analysis_interface')
    ]

    results = self.diagnostics.run_diagnostics(files_to_verify, modules_to_verify)
    if not all(results.values()):
      logger.error("Memoriaエコシステムの検証に失敗しました。再生成を試みます。")
      self.initialize_memoria_ecosystem()
      results = self.diagnostics.run_diagnostics(files_to_verify, modules_to_verify)
      if not all(results.values()):
        logger.critical("再生成後もMemoriaエコシステムの検証に失敗しました。一部のMemoria機能が損なわれる可能性があります。")
      else:
        logger.info("再生成の試行後、Memoriaエコシステムが正常に検証されました。")
    else:
      logger.info("Memoriaエコシステムが正常に検証されました。")


class CodebaseHealthModeler:
  """
    高度な分析を用いて、数学的多様体を使用してコードベースの健全性をモデル化します。

    このクラスは、安定性やテストカバレッジなど、コードベースの健全性のさまざまな側面を
    モデル化するために、数学的射影を読み込み、検証し、適用するメソッドを提供します。
    """
  def __init__(self, bootstrapper: 'IntellisenseBootstrapper'):
    """
    CodebaseHealthModelerを初期化します。

    Args:
        bootstrapper (IntellisenseBootstrapper): ブートストラッパーのインスタンス。
    """
    self.bootstrapper = bootstrapper
    self.registry_path = Path("codebase_health_registry.json")
    self.projections: Dict[str, Dict[str, Any]] = {}
    self._invocations = 0
    self._successful_invocations = 0
    self._total_latency = 0.0

    self.load_registry()
    self.projection_funcs = {
      "stability_projection_v1": self._stability_projection_v1,
      "coverage_projection_v1": self._coverage_projection_v1
    }
    logger.info("CodebaseHealthModelerが初期化されました。")

  def _start_op(self):
    """メトリック追跡のために操作の開始をマークします。"""
    self._invocations += 1
    return time.perf_counter()

  def _end_op(self, start_time: float, success: bool = True):
    """メトリック追跡のために操作の終了をマークします。"""
    latency = time.perf_counter() - start_time
    self._total_latency += latency
    if success:
      self._successful_invocations += 1

  def get_operational_metrics(self) -> Dict[str, Any]:
    """
    モジュールの運用メトリクスを取得します。

    Returns:
        Dict[str, Any]: 運用メトリクスの辞書。
    """
    success_rate = (self._successful_invocations / self._invocations) if self._invocations > 0 else 0.0
    avg_latency_ms = (self._total_latency / self._invocations * 1000) if self._invocations > 0 else 0.0
    return {
      "invocations": self._invocations,
      "success_count": self._successful_invocations,
      "error_count": self._invocations - self._successful_invocations,
      "success_rate": round(success_rate, 4),
      "avg_latency_ms": round(avg_latency_ms, 2)
    }

  def load_registry(self):
    """ディスクから射影レジストリを読み込みます。存在しない場合はデフォルトを作成します。"""
    op_start_time = self._start_op()
    try:
      if not self.registry_path.exists():
        self._create_default_registry()
      with open(self.registry_path, 'r', encoding='utf-8') as f:
        self.projections = json.load(f)
      logger.info(f"[CodebaseHealthModeler] {len(self.projections)}個の射影を読み込みました。")
      self._end_op(op_start_time, success=True)
    except Exception as e:
      logger.error(f"[CodebaseHealthModeler] レジストリの読み込みエラー: {e}")
      self._end_op(op_start_time, success=False)
      raise


  def _create_default_registry(self):
    """デフォルトの射影レジストリファイルを作成します。"""
    op_start_time = self._start_op()
    try:
      default_data = {
        "CODE_STABILITY_V1": {
          "equation_name": "stability_projection_v1",
          "description": "サイクロマティック複雑度とリスクを高曲率曲面としてモデル化します。",
          "version": "1.0",
          "last_verified_at": datetime.now(timezone.utc).isoformat(),
          "status": "active",
          "metadata": {"domain": "code_stability"}
        },
        "TEST_COVERAGE_POTENTIAL": {
          "equation_name": "coverage_projection_v1",
          "description": "テストカバレッジをポテンシャル井戸としてモデル化します。",
          "version": "1.0",
          "last_verified_at": datetime.now(timezone.utc).isoformat(),
          "status": "active",
          "metadata": {"domain": "test_coverage"}
        }
      }
      with open(self.registry_path, 'w', encoding='utf-8') as f:
        json.dump(default_data, f, indent=2)
      logger.info("[CodebaseHealthModeler] デフォルトレジストリを作成しました。")
      self._end_op(op_start_time, success=True)
    except Exception as e:
      logger.error(f"デフォルトレジストリの作成エラー: {e}")
      self._end_op(op_start_time, success=False)
      raise


  def _get_param(self, name: str, default: float) -> float:
    """設定からパラメータ値を取得します。"""
    return self.bootstrapper.config.get('parameters', {}).get(name, {}).get('value', default)

  def _stability_projection_v1(self, complexity: float, risk: float) -> float:
    """コード安定性のための射影関数。"""
    if np is None: raise ImportError("NumPyが必要です。")
    stability = self._get_param('stability_factor', 1.0)
    return float(complexity * np.exp(-risk / stability))

  def _coverage_projection_v1(self, coverage: float, lines: float) -> float:
    """テストカバレッジのための射影関数。"""
    if np is None: raise ImportError("NumPyが必要です。")
    target = self._get_param('coverage_target', 0.85)
    return float(-np.log(max(0.01, target - coverage)) * lines)

  def get_projection(self, name: str) -> Optional[Dict[str, Any]]:
    """
    名前付き射影のメタデータを取得します。

    Args:
        name (str): 射影の名前。

    Returns:
        Optional[Dict[str, Any]]: 射影メタデータ、見つからない場合はNone。
    """
    op_start_time = self._start_op()
    proj = self.projections.get(name)
    if proj and proj.get('status') == 'active':
      self._end_op(op_start_time, success=True)
      return proj
    logger.warning(f"射影 '{name}' が見つからないか、アクティブではありません。")
    self._end_op(op_start_time, success=False)
    return None

  def get_projection_function(self, proj_name: str) -> Optional[Callable]:
    """
    名前付き射影の呼び出し可能な関数を取得します。

    Args:
        proj_name (str): 射影の名前。

    Returns:
        Optional[Callable]: 射影関数、見つからない場合はNone。
    """
    projection_info = self.get_projection(proj_name)
    if projection_info:
      func_name = projection_info.get("equation_name")
      return self.projection_funcs.get(func_name)
    logger.warning(f"射影関数 '{proj_name}' が見つかりません。デフォルトを使用します。")
    return None

  def _curvature_analysis(self, func: Callable, u_grid: np.ndarray, r_grid: np.ndarray) -> Tuple[float, float]:
    """射影関数に対して曲率分析を実行します。"""
    if np is None: return 0.0, 0.0
    try:
      Z = np.array([[func(u, r) for u in u_grid[0,:]] for r in r_grid[:,0]])
      if Z.shape != u_grid.shape:
        if Z.size == u_grid.size: Z = Z.reshape(u_grid.shape)
        else: logger.debug(f"調整不可能な形状の不一致。曲率分析をスキップします。"); return 0.0, 0.0
      dZ_du = np.gradient(Z, axis=1)
      dZ_dr = np.gradient(Z, axis=0)
      d2Z_du2 = np.gradient(dZ_du, axis=1)
      d2Z_dr2 = np.gradient(dZ_dr, axis=0)
      d2Z_dudr = np.gradient(dZ_du, axis=0)
      E = 1 + dZ_du**2; F = dZ_du * dZ_dr; G = 1 + dZ_dr**2
      norm_factor = np.sqrt(1 + dZ_du**2 + dZ_dr**2); denominator_second_form = norm_factor + 1e-9
      L = d2Z_du2 / denominator_second_form; M = d2Z_dudr / denominator_second_form; N = d2Z_dr2 / denominator_second_form
      det_first_form = E * G - F * F; valid_indices = det_first_form > 1e-12
      k_values = np.zeros_like(det_first_form); h_values = np.zeros_like(det_first_form)
      if np.any(valid_indices):
        k_values[valid_indices] = (L[valid_indices] * N[valid_indices] - M[valid_indices]**2) / det_first_form[valid_indices]
        h_values[valid_indices] = (E[valid_indices] * N[valid_indices] - 2 * F[valid_indices] * M[valid_indices] + G[valid_indices] * L[valid_indices]) / (2 * det_first_form[valid_indices])
      finite_k_values = k_values[np.isfinite(k_values)]; finite_h_values = h_values[np.isfinite(h_values)]
      mean_gaussian_curvature = np.mean(np.abs(finite_k_values)) if finite_k_values.size > 0 else 0.0
      mean_mean_curvature = np.mean(np.abs(finite_h_values)) if finite_h_values.size > 0 else 0.0
      return float(mean_mean_curvature), float(mean_gaussian_curvature)
    except Exception as e: logger.debug(f"曲率分析に失敗しました: {e}。0.0, 0.0を返します。"); return 0.0, 0.0

  def _wavelet_analysis(self, func: Callable, u_sample: np.ndarray) -> Optional[float]:
    """射影関数に対してウェーブレット分析を実行します。"""
    if pywt is None or np is None: return None
    try:
      r_fixed_value = np.mean(u_sample)
      z_series = np.array([func(u, r_fixed_value) for u in u_sample])
      if z_series.ndim > 1: z_series = z_series.flatten()
      z_series = z_series[np.isfinite(z_series)]
      if len(z_series) < 2: logger.debug("フィルタリング後のウェーブレット分析用の有限データが不足しています。"); return 0.0
      wavelet_name = 'db1'; max_level = pywt.dwt_max_level(len(z_series), wavelet_name)
      level_to_use = min(3, max_level if max_level > 0 else 0)
      if level_to_use == 0: logger.debug("ウェーブレット分析レベルが0です。短すぎる系列の分析をスキップします。"); return 0.0
      coeffs = pywt.wavedec(z_series, wavelet_name, level=level_to_use)
      if len(coeffs) < 2: return 0.0
      detail_coeffs_std = [np.std(c) for c in coeffs[1:] if len(c) > 0]
      return float(np.max(detail_coeffs_std)) if detail_coeffs_std else 0.0
    except Exception as e: logger.debug(f"ウェーブレット分析に失敗しました: {e}。Noneを返します。"); return None

  def verify_projection(self, proj_name: str, u_range: Tuple[float, float], r_range: Tuple[float, float]) -> bool:
    """
    数学的特性を分析して射影を検証します。

    Args:
        proj_name (str): 検証する射影の名前。
        u_range (Tuple[float, float]): 最初の入力変数の範囲。
        r_range (Tuple[float, float]): 2番目の入力変数の範囲。

    Returns:
        bool: 射影が検証された場合はTrue、それ以外の場合はFalse。
    """
    op_start_time = self._start_op()
    proj_func = self.get_projection_function(proj_name)
    if proj_func is None or np is None:
      logger.warning(f"射影 '{proj_name}' を検証できません: 関数またはNumPyが利用できません。"); self._end_op(op_start_time, success=False); return False
    try:
      u_sample = np.linspace(u_range[0], u_range[1], 10)
      r_sample = np.linspace(r_range[0], r_range[1], 10)
      U_grid, R_grid = np.meshgrid(u_sample, r_sample)
      Z_grid = np.array([[proj_func(u, r) for u in u_sample] for r in r_sample])
      if not isinstance(Z_grid, np.ndarray) or Z_grid.ndim < 2: Z_grid = np.atleast_2d(Z_grid)
      if not np.all(np.isfinite(Z_grid)): logger.warning(f"射影 '{proj_name}' は非有限値を返しました。"); self._end_op(op_start_time, success=False); return False
      mean_z, var_z = np.mean(Z_grid), np.var(Z_grid)
      mean_curv, gauss_curv = self._curvature_analysis(proj_func, U_grid, R_grid)
      wavelet_check_result = True
      if self.bootstrapper.config.get('wavelet_enabled', False) and pywt:
        wavelet_analysis_value = self._wavelet_analysis(proj_func, u_sample)
        wavelet_check_result = (wavelet_analysis_value is not None) and (wavelet_analysis_value > 0.001)
      logger.info(f"検証 '{proj_name}' - 平均: {mean_z:.4f}, 分散: {var_z:.4f}, 平均曲率: {mean_curv:.4f}, ガウス曲率: {gauss_curv:.4f}, ウェーブレットチェック: {wavelet_check_result}")
      self._end_op(op_start_time, success=True)
      return var_z > 0.0001 and mean_curv > 0.0001 and wavelet_check_result
    except Exception as e:
      logger.error(f"'{proj_name}' の検証中にエラーが発生しました: {e}"); self._end_op(op_start_time, success=False); return False

  def health_check(self) -> bool:
    """
    モジュールのヘルスチェックを実行します。

    Returns:
        bool: モジュールが正常な場合はTrue、それ以外の場合はFalse。
    """
    return self.registry_path.exists()

class DeveloperPersonaEngine:
  """
    コンテキストと緊急度に基づいて、開発者のアーキタイプに合わせてAIの提案を形成します。

    このエンジンは、開発者の認識されたニーズによりよく適合するように、応答のトーンと
    信頼度を動的に調整します。
    """
  def __init__(self, bootstrapper: 'IntellisenseBootstrapper'):
    """
    DeveloperPersonaEngineを初期化します。

    Args:
        bootstrapper (IntellisenseBootstrapper): ブートストラッパーのインスタンス。
    """
    self.bootstrapper = bootstrapper
    self.persona_traits = self.bootstrapper.config['developer_persona']
    self._invocations = 0
    self._successful_invocations = 0
    self._total_latency = 0.0
    self.state_history = []
    logger.info("DeveloperPersonaEngineが初期化されました。")

  def _start_op(self):
    """メトリック追跡のために操作の開始をマークします。"""
    self._invocations += 1; return time.perf_counter()
  def _end_op(self, start_time: float, success: bool = True):
    """メトリック追跡のために操作の終了をマークします。"""
    latency = time.perf_counter() - start_time; self._total_latency += latency
    if success: self._successful_invocations += 1

  def get_operational_metrics(self) -> Dict[str, Any]:
    """
    モジュールの運用メトリクスを取得します。

    Returns:
        Dict[str, Any]: 運用メトリクスの辞書。
    """
    success_rate = (self._successful_invocations / self._invocations) if self._invocations > 0 else 0.0
    avg_latency_ms = (self._total_latency / self._invocations * 1000) if self._invocations > 0 else 0.0
    return {
      "invocations": self._invocations, "success_count": self._successful_invocations, "error_count": self._invocations - self._successful_invocations,
      "success_rate": round(success_rate, 4), "avg_latency_ms": round(avg_latency_ms, 2)
    }

  def update_persona(self, context: Dict[str, Any], urgency: float, reward: float):
    """
    現在のコンテキスト、緊急度、フィードバックに基づいて開発者のペルソナを更新します。

    Args:
        context (Dict[str, Any]): 対話のコンテキスト。
        urgency (float): 計算された緊急度レベル。
        reward (float): 前のターンからのフィードバック報酬。
    """
    op_start_time = self._start_op(); success = False
    try:
      effective_urgency = urgency if urgency is not None else self.persona_traits.get('urgency_level', 0.5)
      if effective_urgency > 0.8 or reward < -5.0:
        self.persona_traits['tone'] = 'authoritative'; self.persona_traits['confidence_level'] = min(1.0, self.persona_traits.get('confidence_level', 0.7) + 0.1)
      else:
        self.persona_traits['tone'] = 'collaborative'; self.persona_traits['confidence_level'] = max(0.5, self.persona_traits.get('confidence_level', 0.7) - 0.1)
      self.persona_traits['urgency_level'] = effective_urgency
      self.state_history.append({"context": context, "urgency": effective_urgency, "reward": reward, "timestamp": datetime.now(timezone.utc).isoformat()})
      self.bootstrapper.config['developer_persona'] = self.persona_traits
      self.bootstrapper.save_config()
      success = True
    finally:
      self._end_op(op_start_time, success)

  def shape_response(self, base_response: str, urgency: float) -> str:
    """
    現在の開発者ペルソナに従って、基本応答を形成します。

    Args:
        base_response (str): 形成する基本応答。
        urgency (float): 現在の緊急度レベル。

    Returns:
        str: 形成された応答。
    """
    op_start_time = self._start_op(); success = False
    try:
      confidence = self.persona_traits.get('confidence_level', 0.7)
      tone = self.persona_traits.get('tone', 'collaborative')
      prefix = "重要: " if tone == 'authoritative' else "提案: "
      final_response = f"{prefix}{base_response}"
      if confidence > 0.8 and random.random() < 0.1: final_response += " (分析に基づき強く推奨)"
      success = True
      return final_response.strip()
    finally:
      self._end_op(op_start_time, success)

  def health_check(self) -> bool:
    """
    モジュールのヘルスチェックを実行します。

    Returns:
        bool: モジュールが正常な場合はTrue、それ以外の場合はFalse。
    """
    return bool(self.persona_traits)

class DiagnosticUrgencySystem:
  """
    文脈的な勢いとコードメトリクスに基づいて、焦点と緊急度を定量化します。

    このシステムは、ユーザー入力とコードメトリクスを分析して状況の緊急度を判断し、
    AIの応答を導くために使用できます。
    """
  def __init__(self, bootstrapper: 'IntellisenseBootstrapper'):
    """
    DiagnosticUrgencySystemを初期化します。

    Args:
        bootstrapper (IntellisenseBootstrapper): ブートストラッパーのインスタンス。
    """
    self.bootstrapper = bootstrapper
    self.diagnostic_keywords = self.bootstrapper.config['diagnostic_keywords']
    self.urgency_level = self.bootstrapper.config['developer_persona']['urgency_level']
    self._invocations = 0
    self._successful_invocations = 0
    self._total_latency = 0.0
    logger.info("DiagnosticUrgencySystemが初期化されました。")

  def _start_op(self):
    """メトリック追跡のために操作の開始をマークします。"""
    self._invocations += 1; return time.perf_counter()
  def _end_op(self, start_time: float, success: bool = True):
    """メトリック追跡のために操作の終了をマークします。"""
    latency = time.perf_counter() - start_time; self._total_latency += latency
    if success: self._successful_invocations += 1

  def get_operational_metrics(self) -> Dict[str, Any]:
    """
    モジュールの運用メトリクスを取得します。

    Returns:
        Dict[str, Any]: 運用メトリクスの辞書。
    """
    success_rate = (self._successful_invocations / self._invocations) if self._invocations > 0 else 0.0
    avg_latency_ms = (self._total_latency / self._invocations * 1000) if self._invocations > 0 else 0.0
    return {
      "invocations": self._invocations, "success_count": self._successful_invocations, "error_count": self._invocations - self._successful_invocations,
      "success_rate": round(success_rate, 4), "avg_latency_ms": round(avg_latency_ms, 2)
    }

  def analyze_context(self, user_input: str, code_metrics: Dict[str, Any]) -> float:
    """
    ユーザー入力とコードメトリクスを分析して、コンテキストスコアを決定します。

    Args:
        user_input (str): ユーザーの入力テキスト。
        code_metrics (Dict[str, Any]): コードメトリクスの辞書。

    Returns:
        float: 計算されたコンテキストスコア。
    """
    op_start_time = self._start_op(); success = False
    try:
      input_lower = user_input.lower()
      critical_score = sum(input_lower.count(kw) for kw in self.diagnostic_keywords.get('critical', []))
      warning_score = sum(input_lower.count(kw) for kw in self.diagnostic_keywords.get('warning', []))
      complexity_threshold = self.bootstrapper.config['parameters']['complexity_threshold']['value']
      coverage_target = self.bootstrapper.config['parameters']['coverage_target']['value']
      complexity_score = (code_metrics.get('complexity', 0.0) / complexity_threshold) if complexity_threshold else 0.0
      coverage_score = (1.0 - (code_metrics.get('coverage', 0.0) / coverage_target)) if coverage_target else 0.0
      weighted_sum = (critical_score * 0.5 + warning_score * 0.2 + min(complexity_score, 1.0) * 0.2 + min(coverage_score, 1.0) * 0.1)
      word_count = len(input_lower.split())
      success = True
      return weighted_sum / (word_count + 1) if word_count > 0 else 0.0
    finally:
      self._end_op(op_start_time, success)

  def update_urgency(self, context_score: float, momentum: float):
    """
    コンテキストスコアと勢いに基づいて緊急度レベルを更新します。

    Args:
        context_score (float): 分析からのコンテキストスコア。
        momentum (float): コードベースの健全性の勢い。
    """
    op_start_time = self._start_op(); success = False
    try:
      urgency_delta = 0.05 if momentum > 0 else (-0.05 if momentum < 0 else 0.0)
      self.urgency_level += urgency_delta + (context_score * 0.1)
      self.urgency_level = max(0.0, min(1.0, self.urgency_level))
      self.bootstrapper.config['developer_persona']['urgency_level'] = self.urgency_level
      self.bootstrapper.save_config()
      success = True
    finally:
      self._end_op(op_start_time, success)

  def get_urgency_level(self) -> float:
    """
    現在の緊急度レベルを取得します。

    Returns:
        float: 現在の緊急度レベル。
    """
    return self.urgency_level

  def health_check(self) -> bool:
    """
    モジュールのヘルスチェックを実行します。

    Returns:
        bool: モジュールが正常な場合はTrue、それ以外の場合はFalse。
    """
    return bool(self.diagnostic_keywords)

class ModuleStateTracker:
  """モジュールの運用状態の永続的なスナップショットを管理します。"""
  def __init__(self, db_path: Path):
    """
    ModuleStateTrackerを初期化します。

    Args:
        db_path (Path): SQLiteデータベースファイルへのパス。
    """
    self.db_path = db_path
    self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
    self._create_table()
    logger.info(f"ModuleStateTrackerがDB: {db_path} で初期化されました")

  def _create_table(self):
    """モジュールスナップショット用のデータベーステーブルが存在しない場合に作成します。"""
    with self.conn:
      self.conn.execute("""
        CREATE TABLE IF NOT EXISTS module_snapshots (
          timestamp TEXT NOT NULL,
          module_name TEXT NOT NULL,
          status TEXT, -- health_checkから
          invocations INTEGER DEFAULT 0,
          success_count INTEGER DEFAULT 0,
          error_count INTEGER DEFAULT 0,
          avg_latency_ms REAL DEFAULT 0.0,
          last_error_message TEXT,
          config_snapshot_json TEXT, -- スナップショット時の関連設定
          performance_metrics_json TEXT, -- CPU、メモリなどのモジュール関連の他のメトリクス
          PRIMARY KEY (timestamp, module_name)
        );
      """)
      self.conn.execute("CREATE INDEX IF NOT EXISTS idx_module_name ON module_snapshots (module_name);")
      self.conn.execute("CREATE INDEX IF NOT EXISTS idx_snapshot_time ON module_snapshots (timestamp DESC);")
    logger.info("モジュールスナップショットDBテーブルが作成/検証されました。")

  def record_snapshot(self, snapshot_data: Dict[str, Any]):
    """
    モジュールの状態と運用メトリクスの単一のスナップショットを記録します。

    Args:
        snapshot_data (Dict[str, Any]): スナップショットデータの辞書。
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    module_name = snapshot_data.get('module_name')
    if not module_name:
      logger.error("'module_name'なしでスナップショットを記録しようとしました。スキップします。")
      return

    with self.conn:
      self.conn.execute(
        """INSERT OR REPLACE INTO module_snapshots (timestamp, module_name, status, invocations, success_count, error_count, avg_latency_ms, last_error_message, config_snapshot_json, performance_metrics_json)
          VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (timestamp,
         module_name,
         snapshot_data.get('status', 'UNKNOWN'),
         snapshot_data.get('invocations', 0),
         snapshot_data.get('success_count', 0),
         snapshot_data.get('error_count', 0),
         snapshot_data.get('avg_latency_ms', 0.0),
         snapshot_data.get('last_error_message'),
         json.dumps(snapshot_data.get('config_snapshot')) if snapshot_data.get('config_snapshot') else None,
         json.dumps(snapshot_data.get('performance_metrics')) if snapshot_data.get('performance_metrics') else None)
      )
    logger.debug(f"モジュール: {module_name} のスナップショットを {timestamp} に記録しました")

  def retrieve_latest_snapshots(self, criteria: Optional[Dict[str, Any]] = None, limit: int = 10) -> List[Dict[str, Any]]:
    """
    基準に基づいて最新のスナップショットを取得します。

    基準が提供されない場合、各モジュールの単一の最新スナップショットを取得します。

    Args:
        criteria (Optional[Dict[str, Any]], optional): スナップショットをフィルタリングするための
            基準の辞書。デフォルトはNoneです。
        limit (int, optional): 返すスナップショットの最大数。
            デフォルトは10です。

    Returns:
        List[Dict[str, Any]]: スナップショット辞書のリスト。
    """
    query = """
      SELECT T1.*
      FROM module_snapshots T1
      INNER JOIN (
        SELECT module_name, MAX(timestamp) as max_timestamp
        FROM module_snapshots
        GROUP BY module_name
      ) AS T2
      ON T1.module_name = T2.module_name AND T1.timestamp = T2.max_timestamp
    """
    params: List[Any] = []

    if criteria:
      where_clauses = []
      if 'module_name' in criteria:
        where_clauses.append("T1.module_name = ?")
        params.append(criteria['module_name'])
      if 'status' in criteria:
        where_clauses.append("T1.status = ?")
        params.append(criteria['status'])
      if 'min_avg_latency_ms' in criteria:
        where_clauses.append("T1.avg_latency_ms >= ?")
        params.append(criteria['min_avg_latency_ms'])
      if 'max_error_count' in criteria:
        where_clauses.append("T1.error_count <= ?")
        params.append(criteria['max_error_count'])

      if where_clauses:
        query += " WHERE " + " AND ".join(where_clauses)

    query += " ORDER BY T1.timestamp DESC LIMIT ?"
    params.append(limit)

    results = []
    try:
      with self.conn:
        cursor = self.conn.execute(query, tuple(params))
        column_names = [description[0] for description in cursor.description]
        for row in cursor.fetchall():
          row_dict = dict(zip(column_names, row))
          if row_dict['config_snapshot_json']:
            row_dict['config_snapshot'] = json.loads(row_dict['config_snapshot_json'])
          if row_dict['performance_metrics_json']:
            row_dict['performance_metrics'] = json.loads(row_dict['performance_metrics_json'])

          results.append(row_dict)
    except Exception as e:
      logger.error(f"最新のモジュールスナップショットの取得中にエラーが発生しました: {e}")
    return results

  def health_check(self) -> bool:
    """
    モジュールのヘルスチェックを実行します。

    Returns:
        bool: モジュールが正常な場合はTrue、それ以外の場合はFalse。
    """
    try:
      self.conn.execute("SELECT 1")
      return self.conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='module_snapshots';").fetchone() is not None
    except Exception as e:
      logger.error(f"ModuleStateTracker DBのヘルスチェックに失敗しました: {e}")
      return False

  def shutdown(self):
    """SQLiteデータベース接続を閉じます。"""
    if self.conn:
        self.conn.close()
        logger.info(f"ModuleStateTracker DB接続が {self.db_path} のために閉じられました。")

class MetaReflectionEngine:
  """提案フィードバックとシステムログを分析して、診断戦略を改善します。"""
  def __init__(self, bootstrapper: 'IntellisenseBootstrapper'):
    """
    MetaReflectionEngineを初期化します。

    Args:
        bootstrapper (IntellisenseBootstrapper): ブートストラッパーのインスタンス。
    """
    self.bootstrapper = bootstrapper
    self.embedding_provider = bootstrapper.embedding_provider
    self.interaction_count = 0
    self.reflection_threshold = self.bootstrapper.config.get('meta_reflection', {}).get('reflection_interval', 10)
    self.feedback_log_path = Path(self.bootstrapper.config.get('meta_reflection', {}).get('feedback_log_path', 'ai_suggestion_feedback.jsonl'))
    self.assessment_file_path = Path("logs/assessments.jsonl")
    self.log_catalog_db_path = Path("intellisense_log_catalog.db")
    self.synthesis_report_path = Path("logs/intellisense_data_synthesis_report.log")
    self.last_reflection_content = ""
    self.last_processed_log_line = 0
    self.log_reflector_interval_sec = self.bootstrapper.config.get('meta_reflection', {}).get('log_reflector_interval_sec', 600)
    self.log_reflector_window_lines = self.bootstrapper.config.get('meta_reflection', {}).get('log_reflector_window_lines', 50)
    self.diagnostic_keywords = self.bootstrapper.config['diagnostic_keywords']

    self.db_path = Path("intellisense_feedback.db")
    self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
    self._create_feedback_table()

    self.log_catalog_conn = sqlite3.connect(self.log_catalog_db_path, check_same_thread=False)
    self._create_log_catalog_table()
    logger.info("MetaReflectionEngineがログカタログ機能で初期化されました。")
    self.last_log_scan_time = 0

  def _create_feedback_table(self):
    """フィードバックログデータベーステーブルが存在しない場合に作成します。"""
    with self.conn:
      self.conn.execute("""
        CREATE TABLE IF NOT EXISTS feedback_log (
          fingerprint TEXT PRIMARY KEY,
          timestamp TEXT NOT NULL,
          user_input TEXT NOT NULL,
          ai_response TEXT NOT NULL,
          status TEXT,
          reward REAL DEFAULT 0.0,
          user_id TEXT NOT NULL
        );
      """)
      self.conn.execute("CREATE INDEX IF NOT EXISTS idx_user_timestamp ON feedback_log (user_id, timestamp DESC);")
    logger.info("フィードバックログDBテーブルが作成/検証されました。")

  def _create_log_catalog_table(self):
    """ログカタログデータベーステーブルが存在しない場合に作成します。"""
    with self.log_catalog_conn:
      self.log_catalog_conn.execute("""
        CREATE TABLE IF NOT EXISTS log_catalog (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          ingestion_timestamp TEXT NOT NULL,
          source_file TEXT NOT NULL,
          log_timestamp TEXT,
          log_level TEXT,
          content TEXT NOT NULL,
          content_hash TEXT UNIQUE,
          embedding_json TEXT,
          keywords TEXT,
          assessment_score REAL DEFAULT 0.0,
          category TEXT,
          parsed_values_json TEXT,
          context_category_parsed TEXT,
          status TEXT
        );
      """)
      current_columns = [col[1] for col in self.log_catalog_conn.execute("PRAGMA table_info(log_catalog);").fetchall()]
      if 'parsed_values_json' not in current_columns:
        self.log_catalog_conn.execute("ALTER TABLE log_catalog ADD COLUMN parsed_values_json TEXT;")
      if 'context_category_parsed' not in current_columns:
        self.log_catalog_conn.execute("ALTER TABLE log_catalog ADD COLUMN context_category_parsed TEXT;")

      self.log_catalog_conn.execute("CREATE INDEX IF NOT EXISTS idx_log_level_v2 ON log_catalog (log_level);")
      self.log_catalog_conn.execute("CREATE INDEX IF NOT EXISTS idx_assessment_score_v2 ON log_catalog (assessment_score DESC);")
      self.log_catalog_conn.execute("CREATE INDEX IF NOT EXISTS idx_category_v2 ON log_catalog (category);")
      self.log_catalog_conn.execute("CREATE INDEX IF NOT EXISTS idx_context_category_parsed ON log_catalog (context_category_parsed);")
    logger.info("ログカタログDBテーブルが作成/検証され、必要に応じて新しい列が追加されました。")

  def store_feedback(self, user_input: str, ai_response: str, status: str, reward: float, user_id: str):
    """
    開発者のフィードバックをデータベースとログファイルに保存します。

    Args:
        user_input (str): ユーザーの入力。
        ai_response (str): AIの応答。
        status (str): フィードバックのステータス (例: 'accepted')。
        reward (float): フィードバックの報酬スコア。
        user_id (str): フィードバックを提供したユーザーのID。
    """
    feedback_fingerprint = hashlib.sha256(f"{user_input}{ai_response}{datetime.now(timezone.utc).isoformat()}".encode('utf-8')).hexdigest()

    with self.conn:
      self.conn.execute(
        """INSERT OR REPLACE INTO feedback_log
          (fingerprint, timestamp, user_input, ai_response, status, reward, user_id)
          VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (feedback_fingerprint, datetime.now(timezone.utc).isoformat(), user_input, ai_response, status, reward, user_id)
      )

    self.feedback_log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(self.feedback_log_path, 'a', encoding='utf-8') as f:
      json.dump({"fingerprint": feedback_fingerprint, "user_input": user_input, "ai_response": ai_response, "status": status, "reward": reward, "user_id": user_id}, f)
      f.write('\n')
    logger.debug(f"ユーザー {user_id} のフィードバックを保存しました、フィンガープリント: ...{feedback_fingerprint[-12:]}")

  def reflect(self, user_input: str, ai_response: str, user_id: str = "default") -> Optional[str]:
    """
    ユーザーフィードバックに基づいて反省サイクルを実行します。

    Args:
        user_input (str): ユーザーの入力。
        ai_response (str): AIの応答。
        user_id (str, optional): ユーザーのID。デフォルトは "default" です。

    Returns:
        Optional[str]: 反省の概要、またはNone。
    """
    self.interaction_count += 1
    reflection_output = None
    if self.interaction_count % self.reflection_threshold == 0 and self.interaction_count > 0:
      try:
        feedback_data = []
        with self.conn:
          cursor = self.conn.execute("SELECT status, reward FROM feedback_log WHERE user_id = ? ORDER BY timestamp DESC LIMIT 200", (user_id,))
          for status, reward in cursor.fetchall():
            feedback_data.append({"status": status, "reward": reward})

        accepted = len([f for f in feedback_data if f.get('status') == 'accepted'])
        modified = len([f for f in feedback_data if f.get('status') == 'modified'])
        discarded = len([f for f in feedback_data if f.get('status') == 'discarded'])
        avg_reward = np.mean([f['reward'] for f in feedback_data]) if feedback_data else 0.0

        reflection_output = (f"{self.interaction_count}回の対話後の反省: "
                             f"承認済み: {accepted}, 修正済み: {modified}, 破棄済み: {discarded}, 平均報酬: {avg_reward:.2f}. "
                             f"承認率を向上させるために診断戦略を調整しています。")
        self.last_reflection_content = reflection_output
        logger.info(reflection_output)
      except Exception as e:
        logger.error(f"反省に失敗しました: {str(e)}")
    return reflection_output

  def _parse_structured_log_entry(self, content: str) -> Tuple[Dict[str, Any], Optional[str]]:
    """
    構造化された値のログコンテンツを解析し、コンテキストカテゴリを決定します。

    Args:
        content (str): ログエントリのコンテンツ。

    Returns:
        解析された値の辞書とオプションのコンテキストカテゴリ文字列を含むタプル。
    """
    parsed_values: Dict[str, Any] = {}
    context_category: Optional[str] = None

    advanced_parsers = self.bootstrapper.config.get('log_management', {}).get('advanced_parsers', [])

    for parser_config in advanced_parsers:
      regex_patterns = parser_config.get('regex', [])
      default_category = parser_config.get('context_category')

      for pattern_str in regex_patterns:
        match = re.search(pattern_str, content)
        if match:
          for key, value in match.groupdict().items():
            try:
              if isinstance(value, str) and '.' in value and value.replace('.', '', 1).isdigit():
                parsed_values[key] = float(value)
              elif isinstance(value, str) and value.isdigit():
                parsed_values[key] = int(value)
              else:
                parsed_values[key] = value

            except ValueError:
              parsed_values[key] = value

          if default_category:
            context_category = default_category
          return parsed_values, context_category

    return parsed_values, context_category

  def _assess_log_entry(self, content: str, source_file: Path) -> Dict[str, Any]:
    """
    ログエントリを評価し、特徴を抽出し、カタログ化のために準備します。

    このメソッドには、構造化解析と強化された評価スコアが含まれます。

    Args:
        content (str): 生のログエントリコンテンツ。
        source_file (Path): ログファイルへのパス。

    Returns:
        評価されたログデータの辞書。
    """
    level = "UNKNOWN"
    detected_keywords = []
    assessment_score = 0.0
    category = "general"
    log_ts = datetime.now(timezone.utc).isoformat()
    filtered_content = content

    log_patterns = self.bootstrapper.config['log_management']['log_entry_patterns']

    try:
      json_entry = json.loads(content)
      filtered_content = json_entry.get('message', content)
      level = json_entry.get('level', level).upper()
      log_ts = json_entry.get('timestamp', log_ts)
    except json.JSONDecodeError:
      match_simple_log = re.match(log_patterns.get("simple_log", r"^$"), content)
      if match_simple_log:
        groups = match_simple_log.groups()
        if len(groups) >= 3:
          try:
            timestamp_str = groups[0]
            if ',' in timestamp_str:
              log_ts = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S,%f').replace(tzinfo=timezone.utc).isoformat()
            else:
              log_ts = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc).isoformat()
            level = groups[1].upper()
            filtered_content = groups[2].strip()
          except ValueError:
            logger.debug(f"ログエントリからタイムスタンプの解析に失敗しました: {groups[0]}。現在の時刻を使用します。")

    parsed_values, context_category = self._parse_structured_log_entry(filtered_content)

    content_for_keywords = filtered_content.lower()
    for k_type, keywords in self.diagnostic_keywords.items():
      for kw in keywords:
        if kw in content_for_keywords:
          detected_keywords.append(kw)
          if k_type == 'critical':
            assessment_score += 0.6
            category = "critical_event"
          elif k_type == 'warning':
            assessment_score += 0.3
            if category != "critical_event":
              category = "warning_issue"
          elif k_type == 'info':
            assessment_score += 0.1
            if category not in ["critical_event", "warning_issue"]:
              category = "info_update"

    log_patterns = self.bootstrapper.config.get('log_management', {}).get('log_entry_patterns', {})
    if re.search(log_patterns.get("feedback", r"^$"), content_for_keywords):
      category = "feedback_entry"

    embedding = self.embedding_provider.get_embedding(filtered_content)

    content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()

    return {
      "ingestion_timestamp": datetime.now(timezone.utc).isoformat(),
      "source_file": str(source_file),
      "log_timestamp": log_ts,
      "log_level": level,
      "content": content,
      "content_hash": content_hash,
      "embedding_json": json.dumps(embedding) if embedding is not None else None,
      "keywords": json.dumps(list(set(detected_keywords))),
      "assessment_score": min(assessment_score, 1.0),
      "category": category,
      "parsed_values_json": json.dumps(parsed_values) if parsed_values else None,
      "context_category_parsed": context_category,
      "status": "new"
    }

  def _store_log_entry_in_catalog(self, assessed_data: Dict[str, Any]):
    """評価されたログエントリをログカタログデータベースに保存します。"""
    try:
      with self.log_catalog_conn:
        self.log_catalog_conn.execute(
          """INSERT OR IGNORE INTO log_catalog
             (ingestion_timestamp, source_file, log_timestamp, log_level, content, content_hash, embedding_json, keywords, assessment_score, category, parsed_values_json, context_category_parsed, status)
             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
          (assessed_data['ingestion_timestamp'], assessed_data['source_file'], assessed_data['log_timestamp'],
           assessed_data['log_level'], assessed_data['content'], assessed_data['content_hash'],
           assessed_data['embedding_json'], assessed_data['keywords'], assessed_data['assessment_score'],
           assessed_data['category'], assessed_data['parsed_values_json'], assessed_data['context_category_parsed'],
           assessed_data['status'])
        )
        if self.log_catalog_conn.changes() > 0:
          logger.debug(f"{assessed_data['source_file']} からのログエントリをスコア {assessed_data['assessment_score']:.2f} でカタログ化しました")
          if assessed_data['assessment_score'] >= self.bootstrapper.config['log_management']['assessment_threshold_ai_learning']:
            logger.info(f"{assessed_data['source_file']} からのログエントリがAI学習用にフラグ付けされました (スコア: {assessed_data['assessment_score']:.2f})")
            self.log_catalog_conn.execute("UPDATE log_catalog SET status = 'for_ai_learning' WHERE content_hash = ?", (assessed_data['content_hash'],))
        else:
          logger.debug(f"{assessed_data['source_file']} からのログエントリは既にカタログに存在します (ハッシュ: {assessed_data['content_hash'][-8:]})。スキップしました。")
    except Exception as e:
      logger.error(f"ログエントリをカタログに保存できませんでした: {e}")

  def _scan_and_ingest_log_file(self, log_file: Path):
    """
    ログファイルを読み込み、各エントリを評価し、データベースに保存し、ファイルをアーカイブします。
    """
    if not log_file.exists():
      logger.warning(f"ログファイルが見つかりません: {log_file}")
      return

    if log_file.name == "diagnostics.log" or log_file.name == "feedback.jsonl":
        logger.debug(f"永続的なログファイル {log_file.name} のアーカイブをingest_new_logs内でスキップします。")
        try:
            with open(log_file, "r", encoding='utf-8', errors='ignore') as f:
                for line in f:
                    stripped_line = line.strip()
                    if stripped_line:
                        assessed_data = self._assess_log_entry(stripped_line, log_file)
                        self._store_log_entry_in_catalog(assessed_data)
        except Exception as e:
            logger.error(f"永続的なログファイル {log_file} の処理中にエラーが発生しました: {e}")
        return


    logger.info(f"ログファイルをスキャンしています: {log_file}")
    try:
      with open(log_file, "r", encoding='utf-8', errors='ignore') as f:
        for line in f:
          stripped_line = line.strip()
          if stripped_line:
            assessed_data = self._assess_log_entry(stripped_line, log_file)
            self._store_log_entry_in_catalog(assessed_data)

      timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
      archive_name = ARCHIVE_FOLDER / f"{log_file.stem}_{timestamp}{log_file.suffix}"
      try:
          shutil.move(log_file, archive_name)
          logger.info(f"ログファイル {log_file.name} を {archive_name} にアーカイブしました")
      except Exception as e:
          logger.error(f"ログファイル {log_file.name} を {archive_name} にアーカイブできませんでした: {e}")

    except Exception as e:
      logger.error(f"ログファイル {log_file} の処理中にエラーが発生しました: {e}")

  def ingest_new_logs(self):
    """設定されたログパスのスキャンと新しいデータの取り込みを調整します。"""
    if not self.bootstrapper.config.get('log_management', {}).get('enabled', False):
      logger.info("設定でログ管理が無効になっています。ログの取り込みをスキップします。")
      return

    current_time = time.time()
    scan_interval = self.bootstrapper.config['log_management']['scan_interval_sec']

    if current_time - self.last_log_scan_time < scan_interval:
      logger.debug(f"ログスキャンをスキップします: 前回のスキャンからまだ {scan_interval} 秒経過していません。")
      return

    logger.info("スケジュールされたログ取り込みプロセスを開始します。")
    scan_paths_config = self.bootstrapper.config['log_management']['scan_paths']

    processed_files = set()

    for path_str in scan_paths_config:
      current_path = Path(path_str)
      if current_path.is_file():
        if current_path not in processed_files:
          self._scan_and_ingest_log_file(current_path)
          processed_files.add(current_path)
      elif current_path.is_dir():
        for file_in_dir in current_path.rglob('*'):
          if file_in_dir.is_file() and file_in_dir.suffix.lower() in ['.log', '.txt', '.json', '.jsonl'] and file_in_dir.name not in ["intellisense_data_synthesis_report.log", "intellisense_self_test_report.jsonl"]:
            if file_in_dir not in processed_files:
              self._scan_and_ingest_log_file(file_in_dir)
              processed_files.add(file_in_dir)
      else:
        logger.warning(f"設定されたログスキャンパス '{path_str}' が存在しないか、ファイル/ディレクトリではありません。")

    self.last_log_scan_time = current_time
    logger.info("ログ取り込みプロセスが完了しました。")

  def rehydrate_log_data(self, criteria: Dict[str, Any], limit: int = 100) -> List[Dict[str, Any]]:
    """
    指定された基準に基づいて、カタログから処理済みのログデータを取得します。

    Args:
        criteria (Dict[str, Any]): ログをフィルタリングするための基準の辞書。
        limit (int, optional): 返すログの最大数。デフォルトは100です。

    Returns:
        List[Dict[str, Any]]: 再構成されたログデータ辞書のリスト。
    """
    query = "SELECT * FROM log_catalog WHERE 1=1"
    params = []

    if 'log_level' in criteria:
      query += " AND log_level = ?"
      params.append(criteria['log_level'].upper())
    if 'category' in criteria:
      query += " AND category = ?"
      params.append(criteria['category'])
    if 'context_category_parsed' in criteria:
      query += " AND context_category_parsed = ?"
      params.append(criteria['context_category_parsed'])
    if 'assessment_score_min' in criteria:
      query += " AND assessment_score >= ?"
      params.append(criteria['assessment_score_min'])
    if 'assessment_score_max' in criteria:
      query += " AND assessment_score <= ?"
      params.append(criteria['assessment_score_max'])
    if 'keywords_contains' in criteria:
      query += " AND keywords LIKE ?"
      params.append(f"%{criteria['keywords_contains']}%")
    if 'content_contains' in criteria:
      query += " AND content LIKE ?"
      params.append(f"%{criteria['content_contains']}%")
    if 'status' in criteria:
      query += " AND status = ?"
      params.append(criteria['status'])
    if 'max_ingestion_timestamp' in criteria:
      query += " AND ingestion_timestamp <= ?"
      params.append(criteria['max_ingestion_timestamp'])
    if 'min_ingestion_timestamp' in criteria:
      query += " AND ingestion_timestamp >= ?"
      params.append(criteria['min_ingestion_timestamp'])

    query += f" ORDER BY ingestion_timestamp DESC LIMIT ?"
    params.append(limit)

    results = []
    try:
      with self.log_catalog_conn:
        cursor = self.log_catalog_conn.execute(query, tuple(params))
        column_names = [description[0] for description in cursor.description]
        for row in cursor.fetchall():
          row_dict = dict(zip(column_names, row))
          row_dict['embedding'] = json.loads(row_dict['embedding_json']) if row_dict['embedding_json'] else None
          row_dict['keywords'] = json.loads(row_dict['keywords']) if row_dict['keywords'] else []
          row_dict['parsed_values'] = json.loads(row_dict['parsed_values_json']) if row_dict['parsed_values_json'] else {}

          results.append(row_dict)
    except Exception as e:
      logger.error(f"ログデータの再構成中にエラーが発生しました: {e}")
    return results

  def verify_rehydration_process(self, rehydrated_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    再構成されたログデータを分析して、その整合性を検証し、診断を生成します。

    これにより、初期評価プロセスを改善するためのフィードバックが提供されます。

    Args:
        rehydrated_data (List[Dict[str, Any]]): 再構成されたログデータのリスト。

    Returns:
        Dict[str, Any]: 検証メトリクスと診断の辞書。
    """
    metrics: Dict[str, Any] = {
      "total_entries": len(rehydrated_data),
      "log_level_distribution": {},
      "category_distribution": {},
      "parsed_category_distribution": {},
      "avg_assessment_score": 0.0,
      "min_timestamp_ingestion": None,
      "max_timestamp_ingestion": None,
      "min_timestamp_log": None,
      "max_timestamp_log": None,
      "entries_missing_embedding": 0,
      "entries_missing_parsed_values": 0,
      "diagnostics": []
    }

    if not rehydrated_data:
      metrics["diagnostics"].append("検証するデータがありません。")
      return metrics

    all_scores = []
    for entry in rehydrated_data:
      level = entry.get('log_level', 'UNKNOWN')
      category = entry.get('category', 'general')
      parsed_cat = entry.get('context_category_parsed', 'none')
      ingest_ts = entry.get('ingestion_timestamp')
      log_original_ts = entry.get('log_timestamp')

      metrics['log_level_distribution'][level] = metrics['log_level_distribution'].get(level, 0) + 1
      metrics['category_distribution'][category] = metrics['category_distribution'].get(category, 0) + 1
      metrics['parsed_category_distribution'][parsed_cat] = metrics['parsed_category_distribution'].get(parsed_cat, 0) + 1

      all_scores.append(entry.get('assessment_score', 0.0))

      if entry.get('embedding') is None:
        metrics['entries_missing_embedding'] += 1
        metrics['diagnostics'].append(f"{entry.get('source_file')} のエントリ {entry.get('id')} に埋め込みがありません。")

      if not entry.get('parsed_values') and parsed_cat != 'none':
        metrics['entries_missing_parsed_values'] += 1
        metrics['diagnostics'].append(f"{entry.get('source_file')} のエントリ {entry.get('id')} には解析されたカテゴリ '{parsed_cat}' がありますが、構造化された値は見つかりませんでした。")

      if ingest_ts:
        if metrics["min_timestamp_ingestion"] is None or ingest_ts < metrics["min_timestamp_ingestion"]:
          metrics["min_timestamp_ingestion"] = ingest_ts
        if metrics["max_timestamp_ingestion"] is None or ingest_ts > metrics["max_timestamp_ingestion"]:
          metrics["max_timestamp_ingestion"] = ingest_ts

      if log_original_ts:
           if metrics["min_timestamp_log"] is None or log_original_ts < metrics["min_timestamp_log"]:
            metrics["min_timestamp_log"] = log_original_ts
           if metrics["max_timestamp_log"] is None or log_original_ts > metrics["max_timestamp_log"]:
            metrics["max_timestamp_log"] = log_original_ts

    metrics['avg_assessment_score'] = float(np.mean(all_scores))

    if metrics['entries_missing_embedding'] > 0:
      metrics['diagnostics'].append(f"警告: {metrics['entries_missing_embedding']} 件のエントリに埋め込みがありませんでした。埋め込みプロバイダーを確認してください。")
    if metrics['entries_missing_parsed_values'] > 0:
      metrics['diagnostics'].append(f"情報: {metrics['entries_missing_parsed_values']} 件のエントリには解析されたカテゴリがありましたが、特定の値は抽出されませんでした。高度なパーサーの改良を検討してください。")

    logger.info(f"再構成検証結果: {json.dumps(metrics, indent=2)}")
    return metrics

  def generate_synthesis_report(self, similarity_threshold: float = 0.75) -> Path:
    """
    カタログから類似したログエントリをコンパイルして結合し、統合レポートを生成します。

    このレポートは、システムの改善のための自己生成トレーニングデータとして機能します。

    Args:
        similarity_threshold (float, optional): ログエントリをグループ化するための
            類似性しきい値。デフォルトは0.75です。

    Returns:
        Path: 生成された統合レポートへのパス。
    """
    if np is None:
      logger.error("NumPyが利用できないため、統合レポートを生成できません。")
      return Path("")

    logger.info("IntelliSenseデータ統合レポートを生成しています...")

    relevant_logs = self.rehydrate_log_data(
      {'status': 'for_ai_learning',
       'assessment_score_min': self.bootstrapper.config['log_management']['assessment_threshold_ai_learning']
      }, limit=500
    )

    if not relevant_logs:
      logger.info("統合レポートに関連するログが見つかりませんでした。")
      self.synthesis_report_path.parent.mkdir(parents=True, exist_ok=True)
      with open(self.synthesis_report_path, "w", encoding="utf-8") as f:
        f.write(f"IntelliSenseデータ統合レポート - {datetime.now(timezone.utc).isoformat()}Z\n")
        f.write("現時点では統合に関連するログは見つかりませんでした。\n")
      return self.synthesis_report_path

    logs_with_embeddings = [log for log in relevant_logs if log.get('embedding') is not None]
    if not logs_with_embeddings:
      logger.warning("類似性グループ化のための有効な埋め込みを持つログが見つかりませんでした。")
      return self.synthesis_report_path

    try:
      embeddings_np = np.array([log['embedding'] for log in logs_with_embeddings])
      norms = np.linalg.norm(embeddings_np, axis=1)
      normalized_embeddings = embeddings_np / np.where(norms[:, np.newaxis] != 0, norms[:, np.newaxis], 1)
    except Exception as e:
      logger.error(f"統合のための埋め込み変換中にエラーが発生しました: {e}")
      return self.synthesis_report_path

    grouped_logs: List[List[Dict[str, Any]]] = []
    processed_indices = set()

    for i in range(len(normalized_embeddings)):
      if i in processed_indices:
        continue

      current_group = [logs_with_embeddings[i]]
      processed_indices.add(i)

      for j in range(len(normalized_embeddings)):
        if i == j or j in processed_indices:
          continue

        similarity = np.dot(normalized_embeddings[i], normalized_embeddings[j])
        if similarity >= similarity_threshold:
          current_group.append(logs_with_embeddings[j])
          processed_indices.add(j)

      grouped_logs.append(current_group)

    synthesis_entries: List[Dict[str, Any]] = []
    for group_id, group in enumerate(grouped_logs):
      main_log = group[0]

      all_keywords = set()
      all_categories = set()
      all_parsed_categories = set()
      numerical_values: Dict[str, List[Any]] = {}

      for log_entry in group:
        if log_entry.get('keywords'):
          all_keywords.update(log_entry['keywords'])
        all_categories.add(log_entry.get('category'))
        all_parsed_categories.add(log_entry.get('context_category_parsed'))

        if log_entry.get('parsed_values'):
          for k,v in log_entry['parsed_values'].items():
            if isinstance(v, (int, float)):
              numerical_values.setdefault(k, []).append(v)

      summarized_numerical: Dict[str, Any] = {}
      for k,vals in numerical_values.items():
        if vals:
          summarized_numerical[k] = {
            "avg": float(np.mean(vals)),
            "min": float(np.min(vals)),
            "max": float(np.max(vals))
          }

      synthesis_entries.append({
        "synthesis_id": f"group_{group_id}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "group_size": len(group),
        "representative_log": main_log.get('content'),
        "common_keywords": list(all_keywords),
        "common_categories": list(all_categories),
        "common_parsed_categories": list(all_parsed_categories),
        "summarized_numerical_metrics": summarized_numerical,
        "logs_in_group_ids": [log.get('id') for log in group],
        "purpose": "一般的なログパターンのAI学習用トレーニングデータ。"
      })

    self.synthesis_report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(self.synthesis_report_path, "w", encoding="utf-8") as f:
      f.write(f"IntelliSenseデータ統合レポート - {datetime.now(timezone.utc).isoformat()}Z\n")
      f.write(f"{len(relevant_logs)}件の関連ログに基づいて生成。合計{len(synthesis_entries)}件の統合グループ。\n\n")
      for entry in synthesis_entries:
        f.write("--- 統合ロググループ ---\n")
        f.write(json.dumps(entry, indent=2, ensure_ascii=False))
        f.write("\n\n")

    logger.info(f"IntelliSenseデータ統合レポートが生成されました: {self.synthesis_report_path}")
    logger.info("このレポートは、新しいトレーニングデータとしてシステムによって自動的に解析されます。")
    return self.synthesis_report_path

  def health_check(self) -> bool:
    """
    モジュールのヘルスチェックを実行します。

    Returns:
        bool: モジュールが正常な場合はTrue、それ以外の場合はFalse。
    """
    try:
      self.conn.execute("SELECT 1")
      self.log_catalog_conn.execute("SELECT 1")
      return True
    except Exception as e:
      logger.error(f"MetaReflectionEngine DBのヘルスチェックに失敗しました: {e}")
      return False

  def shutdown(self):
    """SQLiteデータベース接続を閉じます。"""
    if self.conn:
        self.conn.close()
        logger.info(f"MetaReflectionEngineフィードバックDB接続が {self.db_path} のために閉じられました。")
    if self.log_catalog_conn:
        self.log_catalog_conn.close()
        logger.info(f"MetaReflectionEngineログカタログDB接続が {self.log_catalog_conn} のために閉じられました。")


class ModuleOrchestrator:
  """IntellisenseSystemモジュールの健全性を管理および監視します。"""
  def __init__(self, system_instance: 'IntellisenseSystem', module_state_tracker: ModuleStateTracker):
    """
    ModuleOrchestratorを初期化します。

    Args:
        system_instance (IntellisenseSystem): メインシステムインスタンス。
        module_state_tracker (ModuleStateTracker): モジュール状態トラッカー。
    """
    self.system = system_instance
    self.modules: Dict[str, Any] = {}
    self.module_state_tracker = module_state_tracker
    self.last_snapshot_time = 0
    logger.info("ModuleOrchestratorが初期化されました。")

  def register_modules(self, modules: Dict[str, Any]):
    """
    オーケストレーターが監視するモジュールを登録します。

    Args:
        modules (Dict[str, Any]): 登録するモジュールの辞書。
    """
    self.modules = modules
    logger.info(f"{len(self.modules)}個のモジュールを監視対象として登録しました。")

  def run_health_checks(self) -> Dict[str, str]:
    """
    登録されているすべてのモジュールでヘルスチェックを実行します。

    Returns:
        Dict[str, str]: ヘルスチェック結果の辞書。
    """
    health_status: Dict[str, str] = {}
    for name, module in self.modules.items():
      try:
        if hasattr(module, 'health_check') and callable(module.health_check):
          is_healthy = module.health_check()
          health_status[name] = "PASSED" if is_healthy else "FAILED"
        else:
          health_status[name] = "N/A"
      except Exception as e:
        logger.error(f"モジュール {name} のヘルスチェックに失敗しました: {e}")
        health_status[name] = "FAILED"
    return health_status

  def snapshot_all_modules_state(self):
    """登録されているすべてのモジュールの運用メトリクスのスナップショットを取得して記録します。"""
    tracking_interval = self.system.bootstrapper.config['module_tracking']['tracking_interval_sec']
    current_time = time.time()

    if current_time - self.last_snapshot_time < tracking_interval:
      logger.debug(f"モジュール状態のスナップショットをスキップします: 前回のスナップショットからまだ {tracking_interval} 秒経過していません。")
      return

    logger.info("モジュール状態のスナップショットを開始します。")
    for name, module in self.modules.items():
      snapshot_data: Dict[str, Any] = {
        "module_name": name,
        "status": "UNKNOWN",
        "config_snapshot": {k:v for k,v in self.system.bootstrapper.config.items() if k not in ['diagnostic_keywords', 'memoria_ecosystem']}
      }
      try:
        is_healthy = False
        if hasattr(module, 'health_check') and callable(module.health_check):
          is_healthy = module.health_check()
          snapshot_data['status'] = "ACTIVE" if is_healthy else "ERROR"
        else:
          snapshot_data['status'] = "ACTIVE"

        if hasattr(module, 'get_operational_metrics') and callable(module.get_operational_metrics):
          operational_metrics = module.get_operational_metrics()
          snapshot_data.update(operational_metrics)
        else:
          snapshot_data.update({
            "invocations": -1, "success_count": -1, "error_count": -1,
            "success_rate": -1.0, "avg_latency_ms": -1.0
          })

        if hasattr(module, 'last_error_message'):
          snapshot_data['last_error_message'] = module.last_error_message
        else:
          snapshot_data['last_error_message'] = None


      except Exception as e:
        logger.error(f"モジュール {name} のスナップショットデータの取得に失敗しました: {e}")
        snapshot_data['status'] = "CRITICAL_ERROR"
        snapshot_data['last_error_message'] = str(e)
        snapshot_data['error_trace'] = traceback.format_exc()

      self.module_state_tracker.record_snapshot(snapshot_data)
    self.last_snapshot_time = current_time
    logger.info("モジュール状態のスナップショットが完了しました。")

  def health_check(self) -> bool:
    """
    モジュールのヘルスチェックを実行します。

    Returns:
        bool: モジュールが正常な場合はTrue、それ以外の場合はFalse。
    """
    return bool(self.modules)


class IntellisenseSystem:
  """
    Citadel Dossier Systemの適応型インテリセンスコアのメインクラス。

    このクラスは、システムの他のすべてのコンポーネントを統合して、
    ソフトウェア開発のためのAI駆動の支援を提供します。
    """
  def __init__(self):
    """IntellisenseSystemとすべてのサブモジュールを初期化します。"""
    self.bootstrapper = IntellisenseBootstrapper()
    self.module_state_tracker = ModuleStateTracker(Path("intellisense_feedback.db"))
    self.modules = {
      'CodebaseHealthModeler': CodebaseHealthModeler(self.bootstrapper),
      'DeveloperPersonaEngine': DeveloperPersonaEngine(self.bootstrapper),
      'DiagnosticUrgencySystem': DiagnosticUrgencySystem(self.bootstrapper),
      'MetaReflectionEngine': MetaReflectionEngine(self.bootstrapper),
    }
    self.modules['ModuleOrchestrator'] = ModuleOrchestrator(self, self.module_state_tracker)

    if self.bootstrapper.config.get('memoria_ecosystem', {}).get('enabled', False):
      try:
        memoria_core = MemoriaCore()
        memoria_core_config = memoria_core.config

        memoria_core.initialize({})
        self.modules['MemoriaCore'] = memoria_core
      except Exception as e:
        logger.error(f"Memoriaエコシステムの初期化中にエラーが発生しました: {e}")

    self.modules['ModuleOrchestrator'].register_modules(self.modules)
    self.last_turn_data: Dict[str, Dict[str, Any]] = {}
    self._last_log_ingest_time = 0
    self._last_synthesis_time = 0
    self._last_module_snapshot_time = 0
    logger.info("IntellisenseSystemが初期化されました。")

  def _get_reward(self, feedback_text: str) -> float:
    """フィードバックテキストに基づいて報酬スコアを計算します。"""
    text = feedback_text.lower()
    if any(w in text for w in ['thanks', 'perfect', 'great', 'correct', 'good job', 'ありがとう', '完璧', '素晴らしい', '正しい', 'よくやった']):
      return 10.0
    if any(w in text for w in ['wrong', 'incorrect', 'bad', 'not helpful', '違う', '正しくない', '悪い', '役に立たない']):
      return -10.0
    if any(w in text for w in ['more details', 'clarify', 'expand', '詳細', '明確化', '展開']):
      return 1.0
    return 0.0

  def process_input(self, user_input: str, code_metrics: Dict[str, Any], user_id: str = "default") -> str:
    """
    ユーザー入力を処理して、AI駆動の提案と分析を提供します。

    Args:
        user_input (str): 開発者からの自然言語クエリ。
        code_metrics (Dict[str, Any]): コード統計の辞書。
        user_id (str, optional): ユーザーの識別子。デフォルトは "default" です。

    Returns:
        str: AIが生成した応答。
    """
    start_time = time.time()

    log_management_config = self.bootstrapper.config.get('log_management', {})
    if log_management_config.get('enabled', False):
      scan_interval = log_management_config.get('scan_interval_sec', 300)
      if time.time() - self._last_log_ingest_time >= scan_interval:
        logger.info(f"スケジュールされたログ取り込みをトリガーします ({scan_interval}s間隔)。")
        self.modules['MetaReflectionEngine'].ingest_new_logs()
        self._last_log_ingest_time = time.time()
      else:
        logger.debug("定期的なログ取り込みをスキップします。間隔が満たされていません。")

      synthesis_interval_mult = log_management_config.get('synthesis_interval_multiplier', 0.5)
      synthesis_interval = scan_interval * synthesis_interval_mult
      if time.time() - self._last_synthesis_time >= synthesis_interval:
        logger.info(f"スケジュールされた統合レポート生成をトリガーします ({synthesis_interval}s間隔)。")
        self.modules['MetaReflectionEngine'].generate_synthesis_report()
        self._last_synthesis_time = time.time()
      else:
        logger.debug("定期的な統合レポートをスキップします。間隔が満たされていません。")

    module_tracking_config = self.bootstrapper.config.get('module_tracking', {})
    if module_tracking_config.get('enabled', False):
      tracking_interval = module_tracking_config.get('tracking_interval_sec', 60)
      if time.time() - self._last_module_snapshot_time >= tracking_interval:
        logger.info(f"スケジュールされたモジュール状態スナップショットをトリガーします ({tracking_interval}s間隔)。")
        self.modules['ModuleOrchestrator'].snapshot_all_modules_state()
        self._last_module_snapshot_time = time.time()
      else:
        logger.debug("定期的なモジュール状態スナップショットをスキップします。間隔が満たされていません。")

    if psutil:
      try:
        cpu_usage = psutil.cpu_percent(interval=None)
        memory_usage = psutil.virtual_memory().percent
        logger.info(f"システムリソース - CPU: {cpu_usage:.1f}%, メモリ: {memory_usage:.1f}%")
        if cpu_usage > self.bootstrapper.config['system_monitoring']['cpu_threshold']:
          logger.warning("高いCPU使用率が検出されました。")
        if memory_usage > self.bootstrapper.config['system_monitoring']['memory_threshold']:
          logger.warning("高いメモリ使用量が検出されました。")
      except Exception as e:
        logger.warning(f"システムリソース統計を取得できませんでした: {e}")

    reward_from_prev_turn = 0.0
    current_user_last_turn_data = self.last_turn_data.get(user_id)
    if current_user_last_turn_data:
      reward_from_prev_turn = self._get_reward(user_input)
      self.modules['MetaReflectionEngine'].store_feedback(
        user_input=current_user_last_turn_data['user_input'],
        ai_response=current_user_last_turn_data['ai_response'],
        status="accepted" if reward_from_prev_turn > 0 else ("discarded" if reward_from_prev_turn < 0 else "modified"),
        reward=reward_from_prev_turn,
        user_id=user_id
        )
      self.last_turn_data[user_id] = None

    context_score = self.modules['DiagnosticUrgencySystem'].analyze_context(user_input, code_metrics)
    self.modules['DiagnosticUrgencySystem'].update_urgency(context_score, momentum=code_metrics.get('momentum', 0.0))
    urgency = self.modules['DiagnosticUrgencySystem'].get_urgency_level()

    self.modules['DeveloperPersonaEngine'].update_persona({"input": user_input, "metrics": code_metrics}, urgency, reward_from_prev_turn)

    base_response = f"分析されたコードメトリクス: 複雑度 {code_metrics.get('complexity', 0.0):.2f}, カバレッジ {code_metrics.get('coverage', 0.0):.2f}"
    shaped_response = self.modules['DeveloperPersonaEngine'].shape_response(base_response, urgency)

    stability_verified = True
    coverage_verified = True
    if np is not None:
      stability_verified = self.modules['CodebaseHealthModeler'].verify_projection("CODE_STABILITY_V1", (0, 10), (0, 1))
      coverage_verified = self.modules['CodebaseHealthModeler'].verify_projection("TEST_COVERAGE_POTENTIAL", (0, 1), (0, 1000))
    else:
      logger.warning("NumPyが利用できないため、コードベースの健全性検証をスキップします。")

    if not (stability_verified and coverage_verified):
      shaped_response += "\n警告: コードベースの健全性射影が潜在的な問題を示しています。"

    if 'MemoriaCore' in self.modules:
      memoria_request = {
        'code_snippet': user_input,
        'performance_metrics': code_metrics,
        'analysis_result': {}
      }
      if 'analysis_interface' in self.modules['MemoriaCore'].modules:
        mock_analysis_result = self.modules['MemoriaCore'].modules['analysis_interface'].process(memoria_request)
        if mock_analysis_result.get('status') == 'success':
          memoria_request['analysis_result'] = mock_analysis_result['analysis_result']

      memoria_result = self.modules['MemoriaCore'].process_request(memoria_request)
      if memoria_result['status'] == 'success':
        shaped_response += f"\nMemoria分析: {json.dumps(memoria_result['data'], indent=2)}"
      else:
        shaped_response += f"\nMemoria処理の問題: {memoria_result.get('status', 'failed')}"


    self.last_turn_data[user_id] = {
      "user_input": user_input,
      "ai_response": shaped_response,
      "status": "pending",
      "reward": 0.0
    }

    reflection_summary = self.modules['MetaReflectionEngine'].reflect(user_input, shaped_response, user_id)
    if reflection_summary:
      shaped_response += f"\n[メタ: {reflection_summary}]"


    latency = time.time() - start_time
    logger.info(f"入力を {latency:.2f} 秒で処理しました。")
    return shaped_response

  def run_self_test(self) -> Dict[str, Any]:
    """
    システム上で自己診断テストのスイートを実行します。

    Returns:
        Dict[str, Any]: テスト結果の辞書。
    """
    logger.info("IntellisenseSystem自己診断テストを実行しています...")
    detailed_test_results: Dict[str, Any] = {
      "timestamp": datetime.now(timezone.utc).isoformat(),
      "overall_status": "UNKNOWN",
      "tests": {}
    }

    def record_test(test_name: str, status: str, message: str, details: Optional[Dict] = None, severity: str = "INFO", recommendation: Optional[str] = None):
      res_details = details or {}
      details = {"message": message, "details": res_details}
      detailed_test_results['tests'][test_name] = {
        "status": status,
        "message": message,
        "details": res_details,
        "severity": severity,
        "recommendation": recommendation
      }
      if status == "FAIL":
        logger.error(f"自己テスト [{test_name}] 失敗: {message}")
      elif status == "WARNING":
        logger.warning(f"自己テスト [{test_name}] 警告: {message}")
      else:
        logger.info(f"自己テスト [{test_name}] 合格: {message}")


    try:
      module_health_status = self.modules['ModuleOrchestrator'].run_health_checks()
      record_test("module_health_check",
                  "PASS" if all(h == "PASSED" for h in module_health_status.values()) else "FAIL",
                  "すべての登録済みモジュールがヘルスチェックに合格しました。" if all(h == "PASSED" for h in module_health_status.values()) else "一部のモジュールがヘルスチェックに失敗しました。",
                  details=module_health_status,
                  severity="INFO" if all(h == "PASSED" for h in module_health_status.values()) else "CRITICAL",
                  recommendation="特定のモジュールの障害を調査してください。" if not all(h == "PASSED" for h in module_health_status.values()) else None)
    except Exception as e:
      record_test("module_health_check", "FAIL", f"モジュールヘルスチェックのオーケストレーションに失敗しました: {e}",
                  details={"error": str(e), "traceback": traceback.format_exc()},
                  severity="CRITICAL", recommendation="ModuleOrchestratorの実装を確認してください。")

    record_test("config_loading",
                "PASS" if bool(self.bootstrapper.config) else "FAIL",
                "システム設定が正常に読み込まれました。" if bool(self.bootstrapper.config) else "システム設定の読み込みに失敗しました。",
                severity="INFO" if bool(self.bootstrapper.config) else "CRITICAL",
                recommendation="intellisense_config.jsonファイルの存在と構文を確認してください。" if not bool(self.bootstrapper.config) else None)

    try:
      test_embedding = self.bootstrapper.embedding_provider.get_embedding("self-test-embedding-string")
      if test_embedding and len(test_embedding) == self.bootstrapper.config['embedding_dimension']:
        record_test("embedding_provider_functionality", "PASS", "埋め込みプロバイダーは機能しており、次元が設定と一致します。",
                    details={"actual_dimension": len(test_embedding)}, severity="INFO")
      else:
        record_test("embedding_provider_functionality", "FAIL", "埋め込みプロバイダーが無効または不一致の埋め込みを返しました。",
                    details={"test_embedding_is_none": test_embedding is None, "actual_dimension": len(test_embedding) if test_embedding else 0, "expected_dimension": self.bootstrapper.config['embedding_dimension']},
                    severity="CRITICAL", recommendation="sentence-transformersのインストールとモデルの読み込みを確認してください。モデルのダウンロードにはインターネットアクセスが必要です。")
    except Exception as e:
      record_test("embedding_provider_functionality", "FAIL", f"埋め込みプロバイダーテストで例外が発生しました: {e}",
                  details={"error": str(e), "traceback": traceback.format_exc()}, severity="CRITICAL",
                  recommendation="sentence-transformersがインストールされ、モデルが正しく読み込まれることを確認してください。")

    codebase_health_status = "SKIPPED"
    codebase_health_message = "NumPyが利用できないため、コードベースの健全性モデリングはスキップされました。"
    codebase_health_severity = "INFO"
    codebase_health_recommendation = "コードベースの健全性の洞察を得るためにnumpyをインストールしてください。"
    codebase_health_details = None

    if np is not None:
      try:
        stability_verified = self.modules['CodebaseHealthModeler'].verify_projection("CODE_STABILITY_V1", (0, 10), (0, 1))
        coverage_verified = self.modules['CodebaseHealthModeler'].verify_projection("TEST_COVERAGE_POTENTIAL", (0, 1), (0, 1000))
        if stability_verified and coverage_verified:
          codebase_health_status = "PASS"
          codebase_health_message = "コードベースの健全性射影が検証されました。"
          codebase_health_severity = "INFO"
        else:
          codebase_health_status = "FAIL"
          codebase_health_message = "一部のコードベースの健全性射影の検証に失敗しました。"
          codebase_health_severity = "WARNING"
          codebase_health_recommendation = "射影方程式と基礎となるデータを確認してください。"
      except Exception as e:
        codebase_health_status = "FAIL"
        codebase_health_message = f"コードベースの健全性モデルの検証に失敗しました: {e}"
        codebase_health_severity = "CRITICAL"
        codebase_health_recommendation = "CodebaseHealthModelerの実装と依存関係を確認してください。"
        codebase_health_details = {"error": str(e), "traceback": traceback.format_exc()}

    record_test("codebase_health_model_verification", codebase_health_status, codebase_health_message,
                details=codebase_health_details, severity=codebase_health_severity, recommendation=codebase_health_recommendation)

    try:
      self.modules['MetaReflectionEngine'].conn.execute("SELECT 1").fetchone()
      record_test("feedback_db_access", "PASS", "フィードバックデータベースにアクセスできます。", severity="INFO")
    except Exception as e:
      record_test("feedback_db_access", "FAIL", f"フィードバックデータベースへのアクセスに失敗しました: {e}",
                  details={"error": str(e), "traceback": traceback.format_exc()}, severity="CRITICAL",
                  recommendation="intellisense_feedback.dbファイルの権限またはSQLiteのインストールを確認してください。")

    try:
      self.modules['MetaReflectionEngine'].log_catalog_conn.execute("SELECT 1").fetchone()
      record_test("log_catalog_db_access", "PASS", "ログカタログデータベースにアクセスできます。", severity="INFO")

      rehydrated_data_sample = self.modules['MetaReflectionEngine'].rehydrate_log_data({'limit': 1})
      if rehydrated_data_sample is not None:
        record_test("log_catalog_rehydration_functional", "PASS", "ログカタログの再構成は機能しています。", severity="INFO")

        rehydration_verification_report = self.modules['MetaReflectionEngine'].verify_rehydration_process(rehydrated_data_sample[:5])
        if rehydration_verification_report and not rehydration_verification_report.get('diagnostics'):
          record_test("log_catalog_rehydration_verification", "PASS", "ログカタログの再構成データが初期検証に合格しました。",
                      details=rehydration_verification_report, severity="INFO")
        else:
          record_test("log_catalog_rehydration_verification", "FAIL", "ログカタログの再構成データに検証の問題がありました。",
                      details=rehydration_verification_report, severity="WARNING", recommendation="診断に基づいてログの解析と評価ロジックを確認してください。")
      else:
        record_test("log_catalog_rehydration_functional", "FAIL", "ログカタログの再構成がNoneまたは空を返しました。",
                    severity="CRITICAL", recommendation="rehydrate_log_dataの実装を確認してください。")

    except Exception as e:
      record_test("log_catalog_db_access", "FAIL", f"ログカタログデータベースのテストに失敗しました: {e}",
                  details={"error": str(e), "traceback": traceback.format_exc()}, severity="CRITICAL",
                  recommendation="intellisense_log_catalog.dbファイルの権限またはSQLiteのインストールを確認してください。テーブルスキーマが正しいことを確認してください。")
      record_test("log_catalog_rehydration_functional", "FAIL", "再構成のためにDBにアクセスできません。", severity="CRITICAL")
      record_test("log_catalog_rehydration_verification", "FAIL", "検証のためにDBにアクセスできません。", severity="CRITICAL")


    try:
      synthesis_path = self.modules['MetaReflectionEngine'].generate_synthesis_report(similarity_threshold=0.9)
      if synthesis_path.exists() and synthesis_path.stat().st_size > 0:
        record_test("synthesis_report_generation", "PASS", "データ統合レポートがコンテンツ付きで正常に生成されました。",
                    details={"report_path": str(synthesis_path), "report_size_bytes": synthesis_path.stat().st_size}, severity="INFO")
      else:
        record_test("synthesis_report_generation", "FAIL", "統合レポートは生成されましたが、空または存在しませんでした。",
                    details={"report_path": str(synthesis_path), "report_exists": synthesis_path.exists()}, severity="WARNING",
                    recommendation="なぜ統合が出力を生成しなかったのかを確認してください。関連するログがないか、類似性しきい値が高すぎる可能性があります。")
    except Exception as e:
      record_test("synthesis_report_generation", "FAIL", f"統合レポートの生成に失敗しました: {e}",
                  details={"error": str(e), "traceback": traceback.format_exc()}, severity="CRITICAL",
                  recommendation="MetaReflectionEngine.generate_synthesis_reportの実装とログデータの可用性を確認してください。")

    try:
      memoria_checks = self.bootstrapper.diagnostics.run_diagnostics(
        [
            self.bootstrapper.memoria_ecosystem_path / 'config' / 'memoria_config.json',
            self.bootstrapper.memoria_ecosystem_path / 'memoria_module.py',
            self.bootstrapper.memoria_ecosystem_path / 'memoria_core.py',
            self.bootstrapper.memoria_ecosystem_path / 'self_reflection.py',
            self.bootstrapper.memoria_ecosystem_path / 'optimization_engine.py',
            self.bootstrapper.memoria_ecosystem_path / 'analysis_interface.py',
        ],
        [
            (self.bootstrapper.memoria_ecosystem_path / 'memoria_module.py', 'ecosystem.memoria.memoria_module'),
            (self.bootstrapper.memoria_ecosystem_path / 'memoria_core.py', 'ecosystem.memoria.memoria_core'),
            (self.bootstrapper.memoria_ecosystem_path / 'self_reflection.py', 'ecosystem.memoria.self_reflection'),
            (self.bootstrapper.memoria_ecosystem_path / 'optimization_engine.py', 'ecosystem.memoria.optimization_engine'),
            (self.bootstrapper.memoria_ecosystem_path / 'analysis_interface.py', 'ecosystem.memoria.analysis_interface')
        ]
      )

      all_memoria_modules_passed = all(memoria_checks.values())
      memoria_overall_status = "PASS" if all_memoria_modules_passed else "FAIL"
      memoria_severity = "INFO" if all_memoria_modules_passed else "WARNING"
      memoria_recommendation = "Memoriaエコシステムのファイルとインポートを確認してください。" if not all_memoria_modules_passed else None

      record_test("memoria_ecosystem_verification",
                  memoria_overall_status,
                  "Memoriaエコシステムのファイルとインポートが正常に検証されました。" if all_memoria_modules_passed else "Memoriaエコシステムの検証に問題がありました (外部ファイル)。",
                  details=memoria_checks,
                  severity=memoria_severity,
                  recommendation=memoria_recommendation)
    except Exception as e:
      record_test("memoria_ecosystem_verification", "FAIL", f"Memoriaエコシステムの検証に失敗しました: {e}",
                  details={"error": str(e), "traceback": traceback.format_exc()}, severity="CRITICAL",
                  recommendation="Memoriaエコシステムのファイルが存在し、構文的に正しいこと、および外部インポートのすべての依存関係が満たされていることを確認してください。")


    if psutil:
      try:
        cpu_before = psutil.cpu_percent(interval=None)
        time.sleep(0.1)
        cpu_after = psutil.cpu_percent(interval=None)
        memory_usage = psutil.virtual_memory().percent
        if cpu_after is not None and memory_usage is not None:
          record_test("system_resource_monitoring", "PASS", "システムリソース監視は機能しています。",
                      details={"cpu_percent_sampled": cpu_after, "memory_percent": memory_usage}, severity="INFO")
        else:
          record_test("system_resource_monitoring", "FAIL", "psutilはインストールされていますが、有効なリソースデータを取得できませんでした。",
                      details={"cpu_after": cpu_after, "memory_usage": memory_usage}, severity="WARNING", recommendation="psutilの権限/設定を確認してください。")
      except Exception as e:
        record_test("system_resource_monitoring", "FAIL", f"システムリソース監視テストに失敗しました: {e}",
                    details={"error": str(e), "traceback": traceback.format_exc()}, severity="WARNING",
                    recommendation="psutilのインストールまたはシステム環境の権限を確認してください。")
    else:
      record_test("system_resource_monitoring", "SKIPPED", "psutilが見つからないため、システムリソース監視はスキップされました。", severity="INFO",
                  recommendation="システムリソースの洞察を得るためにpsutilをインストールしてください。")

    try:
      self.modules['ModuleOrchestrator'].snapshot_all_modules_state()
      latest_snapshots = self.module_state_tracker.retrieve_latest_snapshots(limit=len(self.modules))
      if latest_snapshots and len(latest_snapshots) >= len(self.modules):
        has_valid_metrics = any(s.get('invocations', 0) > -1 for s in latest_snapshots)
        if has_valid_metrics:
          record_test("module_state_tracking", "PASS", "モジュール状態の追跡とスナップショットの記録は機能しています。",
                      details={"num_snapshots": len(latest_snapshots)}, severity="INFO")
        else:
          record_test("module_state_tracking", "WARNING", "モジュール状態の追跡はスナップショットを記録しましたが、運用メトリクスが欠落している可能性があります。",
                      details={"num_snapshots": len(latest_snapshots)}, severity="WARNING", recommendation="モジュールが `get_operational_metrics` を正しく実装していることを確認してください。")
      else:
        record_test("module_state_tracking", "FAIL", "モジュール状態の追跡が期待される数のスナップショットを記録しませんでした。",
                    details={"expected": len(self.modules), "actual": len(latest_snapshots)}, severity="CRITICAL",
                    recommendation="ModuleOrchestrator.snapshot_all_modules_stateとModuleStateTracker.record_snapshotの実装を確認してください。")
    except Exception as e:
      record_test("module_state_tracking", "FAIL", f"モジュール状態追跡テストに失敗しました: {e}",
                  details={"error": str(e), "traceback": traceback.format_exc()}, severity="CRITICAL",
                  recommendation="ModuleStateTrackerとModuleOrchestratorの実装を確認してください。")


    overall_status_list = [t['status'] for t in detailed_test_results['tests'].values() if t['status'] != "SKIPPED"]
    if "FAIL" in overall_status_list: detailed_test_results['overall_status'] = "FAIL"
    elif "WARNING" in overall_status_list: detailed_test_results['overall_status'] = "WARNING"
    elif "PASS" in overall_status_list: detailed_test_results['overall_status'] = "PASS"
    else: detailed_test_results['overall_status'] = "SKIPPED_ALL"

    logger.info(f"自己テスト結果:\n{json.dumps(detailed_test_results, indent=2)}")

    self_test_report_path = Path("logs/intellisense_self_test_report.jsonl")
    self_test_report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(self_test_report_path, "a", encoding="utf-8") as f:
      json.dump(detailed_test_results, f)
      f.write("\n")
    logger.info(f"自己テストレポートを自己再処理のために {self_test_report_path} に保存しました。")

    return detailed_test_results

  def shutdown(self):
      """すべてのIntellisenseSystemモジュールの正常なシャットダウンを実行します。"""
      logger.info("IntellisenseSystemモジュールのシャットダウンを開始しています...")
      for name, module in self.modules.items():
          if name not in ['ModuleOrchestrator', 'MemoriaCore'] and hasattr(module, 'shutdown') and callable(module.shutdown):
              try:
                  module.shutdown()
                  logger.info(f"モジュール {name} が正常にシャットダウンしました。")
              except Exception as e:
                  logger.error(f"モジュール {name} のシャットダウン中にエラーが発生しました: {e}")

      if 'MemoriaCore' in self.modules:
          memoria_core_module = self.modules['MemoriaCore']
          logger.info("MemoriaCore (内部インスタンス) は明示的なシャットダウンを必要とせず、そのサブモジュールは自己管理します。")


  def display_system_summary_grid(self, num_modules_to_display: int = 10):
    """
    最新のモジュール運用スナップショットを取得し、人間が読めるグリッドサマリーをCLIに出力します。
    """
    logger.info("IntelliSenseシステムサマリーグリッドを生成しています...")
    latest_snapshots = self.module_state_tracker.retrieve_latest_snapshots(limit=num_modules_to_display)

    if not latest_snapshots:
      print("\n--- IntelliSenseシステムサマリー ---")
      print("モジュールの運用データはまだ利用できません。システムと対話するか、スケジュールされたスナップショットをお待ちください。")
      print("-----------------------------------")
      return

    headers = ["モジュール", "ステータス", "健全性", "呼び出し回数", "成功率", "平均レイテンシ (ms)", "最後のエラー"]
    rows = []

    col_widths = {header: len(header) for header in headers}

    for snapshot in latest_snapshots:
      module_name = snapshot.get('module_name', 'N/A')
      status = snapshot.get('status', 'N/A')
      health_status_obj = self.modules.get(module_name)
      if health_status_obj and hasattr(health_status_obj, 'health_check') and callable(health_status_obj.health_check):
          try:
              is_healthy = health_status_obj.health_check()
              health_status_str = "HEALTHY" if is_healthy is True else ("UNHEALTHY" if is_healthy is False else "N/A_FUNC")
          except Exception:
              health_status_str = "ERROR_CHECK"
      else:
          health_status_str = "N/A_MOD"

      invocations = snapshot.get('invocations', 0)
      success_rate = f"{snapshot.get('success_rate', 0.0)*100:.1f}%" if snapshot.get('invocations', 0) > 0 else "N/A"
      avg_latency = f"{snapshot.get('avg_latency_ms', 0.0):.2f}" if snapshot.get('invocations') else "N/A"
      last_error = snapshot.get('last_error_message', '') or ''

      module_name_display = (module_name[:18] + '..') if len(module_name) > 20 else module_name
      last_error_display = (last_error[:18] + '..') if len(last_error) > 20 else last_error

      rows.append({
        "モジュール": module_name_display,
        "ステータス": status,
        "健全性": health_status_str,
        "呼び出し回数": str(invocations),
        "成功率": success_rate,
        "平均レイテンシ (ms)": avg_latency,
        "最後のエラー": last_error_display
      })

      for i, header in enumerate(headers):
        col_widths[header] = max(col_widths[header], len(rows[-1][header].encode('utf-8', 'ignore')))

    print("\n" + "=" * (sum(col_widths.values()) + len(headers) * 3 + 1))
    print("IntelliSenseシステム運用スナップショット監査".center(sum(col_widths.values()) + len(headers) * 3 + 1))
    print("=" * (sum(col_widths.values()) + len(headers) * 3 + 1))

    header_line = "│"
    for header in headers:
        header_line += f" {header.ljust(col_widths[header] + header.count('（') + header.count('）'))} │"
    print(header_line)
    print("├" + "─" * (sum(col_widths.values()) + len(headers) * 3 - 1) + "┤")

    for row_data in rows:
        data_line = "│"
        for header in headers:
            cell_value = row_data[header]
            padding = col_widths[header] - (len(cell_value.encode('utf-8')) - len(cell_value))
            data_line += f" {cell_value.ljust(padding)} │"
        print(data_line)

    print("=" * (sum(col_widths.values()) + len(headers) * 3 + 1))
    print(f"データ取得日時: {datetime.now(timezone.utc).isoformat()}Z".rjust(sum(col_widths.values()) + len(headers) * 3 + 1))
    print("=" * (sum(col_widths.values()) + len(headers) * 3 + 1) + "\n")


if __name__ == "__main__":
    # --- 起動前のアーカイブとディレクトリ設定 ---
    # アーカイブフォルダを定義し、存在することを確認する
    ARCHIVE_FOLDER = Path("archive")
    ARCHIVE_FOLDER.mkdir(exist_ok=True)

    # 1. 以前のdiagnostics.logをアーカイブする (前の実行から存在する場合)
    current_diagnostics_log_path = Path("diagnostics.log")
    if current_diagnostics_log_path.exists():
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        archive_name = ARCHIVE_FOLDER / f"diagnostics_log_{timestamp}.log"
        print(f"[{datetime.now().isoformat()}] [INFO] 以前のdiagnostics.logを {archive_name} にアーカイブしています")
        try:
            # 潜在的な以前の暗黙的なハンドラが解放されていることを確認する。
            # これはWindowsのPermissionErrorにとって重要なポイントです。
            # グローバルロガーの設定は__main__の上にあるため、まだファイルを保持している可能性があります。
            # これは、ファイルが移動のために解放されていることを保証する最も安全な方法です。
            old_main_logger_instance = logging.getLogger("IntellisenseSystem")
            for h in old_main_logger_instance.handlers[:]:
                try:
                    h.flush()
                    h.close()
                    old_main_logger_instance.removeHandler(h)
                except Exception as e:
                    print(f"[{datetime.now().isoformat()}] [WARN] 実行前のdiagnostics.logのハンドラクローズ中にエラー: {e}", file=sys.stderr)

            shutil.move(current_diagnostics_log_path, archive_name)
            print(f"[{datetime.now().isoformat()}] [INFO] 以前のdiagnostics.logのアーカイブに成功しました。")
        except Exception as e:
            print(f"[{datetime.now().isoformat()}] [WARN] diagnostics.logのアーカイブに失敗しました: {e}。使用中か存在しない可能性があります。", file=sys.stderr)

    # 古いdiagnostics.logをアーカイブした後、ロギングを明示的に再初期化し、この実行のために新しいことを保証する
    # これにより、diagnostics.logが実行ごとに新しく開始され、すべてのメッセージがそれに追加されることが保証されます。
    main_logger_instance = logging.getLogger("IntellisenseSystem")
    if not main_logger_instance.handlers: # この実行のために新しいハンドラが作成されることを保証する
        _global_file_handler = logging.FileHandler('diagnostics.log', mode='a', encoding='utf-8')
        _global_file_handler.setLevel(logging.INFO)
        file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        _global_file_handler.setFormatter(file_formatter)
        main_logger_instance.addHandler(_global_file_handler)

        _global_console_handler = logging.StreamHandler()
        _global_console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        _global_console_handler.setFormatter(console_formatter)
        main_logger_instance.addHandler(_global_console_handler)

    logger.info("IntellisenseSystemのブートストラップを開始しています...")


    # クリーンアップするパス (一時的/生成されたもののみ、logs/やDBは除く)
    cleanup_paths_initial = [
      "intellisense_config.json",
      "codebase_health_registry.json",
      "ecosystem/" # 起動時に再生成したいため、ここでの削除は問題ありません
    ]

    for path_str in cleanup_paths_initial:
        path = Path(path_str)
        if path.is_file():
            try:
                path.unlink(missing_ok=True)
            except PermissionError as e:
                logger.warning(f"ファイル {path} を削除できませんでした: {e}")
        elif path.is_dir():
            try:
                shutil.rmtree(path, ignore_errors=True)
            except PermissionError as e:
                logger.warning(f"ディレクトリ {path} を削除できませんでした: {e}")


    # logsディレクトリが存在することを確認する (新しいログが作成されるため)
    Path("logs").mkdir(exist_ok=True)

    # 取り込まれるダミーログを作成する。これらはMetaReflectionEngineによってARCHIVEに移動されます。
    dummy_log_files = [] # 後でアーカイブを確認するためにこれらを追跡する

    log_name_1_path = Path("logs/example_app.log")
    with open(log_name_1_path, "w") as f:
        f.write(f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S,%f')} - INFO - アプリが正常に起動しました。PID: 12345。\n")
        f.write(f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S,%f')} - WARNING - 高いメモリ使用量が検出されました。メモリ: 85.23%。CPU: 75.10%。レイテンシ: 123.45ms。\n")
        f.write(f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S,%f')} - ERROR - データベースMainDBへの接続に失敗しました。\n")
    dummy_log_files.append(log_name_1_path)

    log_name_2_path = Path("logs/performance_monitor.log")
    with open(log_name_2_path, "w") as f:
        f.write(f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S,%f')} - INFO - プロセスXは安定して実行されています。CPU: 45.6%, メモリ: 30.1%。\n")
        f.write(f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S,%f')} - WARNING - レイテンシの急上昇が検出されました。レイテンシ: 500.2ms。モジュールSystemCoreが失敗しました: タイムアウト。\n")
    dummy_log_files.append(log_name_2_path)

    log_name_3_path = Path("logs/test_runner.log")
    with open(log_name_3_path, "w") as f:
        f.write(f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S,%f')} - INFO - 実行されたテスト: 100, 失敗: 5, エラー: 0。\n")
        f.write(f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S,%f')} - ERROR - テスト'critical_feature_test'の検証に失敗しました。\n")
    dummy_log_files.append(log_name_3_path)

    log_name_4_path = Path("logs/another_log.jsonl") # これは一貫してlogs/にあります
    with open(log_name_4_path, "w") as f:
        json.dump({"timestamp": datetime.now(timezone.utc).isoformat(), "level": "INFO", "message": "ユーザーログイン成功。"}, f)
        f.write("\n")
        json.dump({"timestamp": datetime.now(timezone.utc).isoformat(), "level": "CRITICAL", "message": "未処理の例外: ゼロ除算。"}, f)
        f.write("\n")
    dummy_log_files.append(log_name_4_path)

    # Memoriaエコシステムファイルの作成 (ブートストラップでまだ存在しない場合)
    Path("ecosystem/memoria").mkdir(parents=True, exist_ok=True)
    Path("ecosystem/memoria/config").mkdir(exist_ok=True)

    # ai_suggestion_feedback.jsonlは永続的で、追記のみされるべき
    feedback_jsonl_path = Path("ai_suggestion_feedback.jsonl")
    if not (feedback_jsonl_path.exists() and feedback_jsonl_path.stat().st_size > 0):
        with open(feedback_jsonl_path, "w") as f:
            json.dump({"performance_score": 0.9, "status": "accepted", "timestamp": datetime.now(timezone.utc).isoformat()}, f)
            f.write("\n")
            json.dump({"performance_score": 0.5, "status": "discarded", "timestamp": datetime.now(timezone.utc).isoformat()}, f)
            f.write("\n")

    # --- システム初期化 ---
    system = IntellisenseSystem()

    # --- 自己テストの実行 ---
    logger.info("\n--- IntellisenseSystem自己テストの実行 ---")
    self_test_detailed_results = system.run_self_test()
    if self_test_detailed_results['overall_status'] == "PASS":
        logger.info("\nすべての重要なIntellisenseSystem自己テストに合格しました！")
    else:
        logger.info(f"\nIntellisenseSystem自己テストがステータス: {self_test_detailed_results['overall_status']} で完了しました。詳細はログを確認してください。")

    # --- 即時ログ取り込みのトリガー ---
    # これは、システムが自身の最新の自己テストレポートと既存のログを取得するために重要です
    logger.info(f"\n--- ログの強制取り込み (自己テストレポートと既存のログを含む) ---")
    system.modules['MetaReflectionEngine'].ingest_new_logs() # これにより、処理済みのファイルがlogs/からARCHIVEに移動されます

    # dummy_log_filesはすでに設定されたスキャンパスにあったため、 अबアーカイブされているはずです。
    # ここでは明示的なアーカイブは行いません。システムは'logs/'からそれらを取得し、移動するように設計されています。

    # --- 即時統合レポート生成のトリガー ---
    logger.info(f"\n--- 統合レポートの強制生成 (新しく取り込まれたデータを処理するため) ---")
    synthesis_report_path = system.modules['MetaReflectionEngine'].generate_synthesis_report()
    if synthesis_report_path.exists():
        logger.info(f"統合レポートは次の場所にあります: {synthesis_report_path}")
        with open(synthesis_report_path, 'r', encoding='utf-8') as f:
            logger.info("\n--- 統合レポートのコンテンツ (最初の500文字) ---")
            logger.info(f.read(500))
            logger.info("...")


    # --- CLIシステムサマリーグリッドの表示 ---
    system.display_system_summary_grid()


    # --- さらなる通常の対話のシミュレーション ---
    logger.info("\n--- さらなる対話のシミュレーション ---")
    mock_code_metrics = {"complexity": 5.0, "coverage": 0.95, "momentum": 0.1}

    response1 = system.process_input("CIパイプラインの最近のパフォーマンスの急上昇を分析してください。", mock_code_metrics, user_id="dev_user_1")
    logger.info(f"\nユーザー1 応答1: {response1}")

    response2 = system.process_input("テストカバレッジのギャップについてはどうですか？", mock_code_metrics, user_id="dev_user_1")
    logger.info(f"\nユーザー1 応答2: {response2}")

    response3 = system.process_input("データシリアライゼーションモジュールのリファクタリングを手伝ってください。複雑すぎます。", {"complexity": 15.0, "coverage": 0.6, "momentum": 0.5}, user_id="dev_user_2")
    logger.info(f"\nユーザー2 応答1: {response3}")

    # 自己テストデータの再構成の検証
    logger.info(f"\n--- 自己テストレポートデータの再構成の検証 ---")
    # 注: self_test_report.jsonlはMetaReflectionEngineによって管理され、デフォルトではingest_new_logsでアーカイブに移動されません
    # なぜなら、それは動的なレポートだからです。アーカイブしたい場合は、_scan_and_ingest_log_fileで処理される明示的なリストに追加してください。
    # 今のところ、それはlogs/に残り、そのコンテンツがスキャンされます。
    rehydrated_self_test_logs = system.modules['MetaReflectionEngine'].rehydrate_log_data(
      {'source_file': str(Path("logs/intellisense_self_test_report.jsonl")), 'limit': 100}
    )
    if rehydrated_self_test_logs:
      logger.info(f"{len(rehydrated_self_test_logs)}件の自己テストログエントリを正常に再構成しました。")
      verification_results_self_test = system.modules['MetaReflectionEngine'].verify_rehydration_process(rehydrated_self_test_logs[:5])
      logger.info(f"自己テストの再構成検証結果: {json.dumps(verification_results_self_test, indent=2)}")
    else:
      logger.info("再構成のためのカタログに自己テストレポートログが見つかりませんでした。")


    logger.info("\n--- シミュレーション完了 ---")

    # --- 最終的なシステムシャットダウンと非永続的なクリーンアップ ---
    # 1. すべてのモジュール固有のDB接続を閉じ、リソースを解放する
    logger.info("IntellisenseSystemの正常なシャットダウンを開始しています...")
    system.shutdown()

    # 2. グローバルロガーハンドラを閉じる
    logger.info("メインロガーハンドラを閉じています...")
    _close_all_global_handlers() # 専用の関数を呼び出す

    # 3. 非永続的なファイル/フォルダのみの最終的なクリーンアップ
    # ログとDB (diagnostics.log, intellisense_feedback.db, intellisense_log_catalog.db)
    # ルートディレクトリ内のものは変更されません。
    # 'logs/'からのログファイルは'archive/'に移動されているはずです。
    # feedback.jsonl (ai_suggestion_feedback.jsonl) は永続的であり、保持されます。
    cleanup_paths_final_non_persistent = [
      "ecosystem/" # 次回の実行時に再生成を保証するためにこれを削除します
    ]
    for path_str in cleanup_paths_final_non_persistent:
        path = Path(path_str)
        if path.is_file():
            try:
                path.unlink(missing_ok=True)
            except PermissionError as e:
                print(f"[{datetime.now().isoformat()}] [WARN] ファイル {path} のリンクを解除できませんでした: {e}", file=sys.stderr)
        elif path.is_dir():
            try:
                shutil.rmtree(path, ignore_errors=True)
            except PermissionError as e:
                print(f"[{datetime.now().isoformat()}] [WARN] ディレクトリ {path} を削除できませんでした: {e}", file=sys.stderr)

    print("\nクリーンアップ完了。非永続的な生成ファイルは削除され、ログとDBは保持/アーカイブされました。")
