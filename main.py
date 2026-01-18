#!/usr/bin/env python3
"""
整合版主控程式
Integrated Main Pipeline

完整流程：
1. shorten_transcript.py (手動)
2. 1topic_spliterG3v2.py  ✅
3. 2chunks_summary.py     ✅  
4. 3brief_summary_reindex.py ✅
5. 4Condense.py          ✅
6. pipeline_meeting_report.py 🆕
7. clean_md.py           🆕
"""

import subprocess, pathlib, sys, os, glob
import time


def run_subprocess_with_stdout(script_name, *args):
    """執行子程式並擷取stdout"""
    cmd = [sys.executable, script_name] + list(args)
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"===== {script_name} STDERR =====", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        sys.exit(result.returncode)
    
    return result.stdout.strip(), result.stderr

def run_1topic_splitter(src_path: str) -> pathlib.Path:
    """第1步：主題分段"""
    print(f"🔄 步驟1: 主題分段 - {src_path}")
    script_path = os.path.join(os.path.dirname(__file__), "1topic_spliterG3v2.py")
    stdout, stderr = run_subprocess_with_stdout(script_path, src_path)
    output_dir = pathlib.Path(stdout)
    print(f"✅ 步驟1完成: {output_dir}")
    return output_dir

def run_2chunks_summary(prev_dir: pathlib.Path) -> pathlib.Path:
    """第2步：生成摘要"""
    print(f"🔄 步驟2: 生成摘要 - {prev_dir}")
    stdout, stderr = run_subprocess_with_stdout("2chunks_summary.py", str(prev_dir))
    output_file = pathlib.Path(stdout)
    print(f"✅ 步驟2完成: {output_file}")
    return output_file

def run_3brief_summary_reindex(prev_file: pathlib.Path) -> pathlib.Path:
    """第3步：摘要重整"""
    print(f"🔄 步驟3: 摘要重整 - {prev_file}")
    stdout, stderr = run_subprocess_with_stdout("3brief_summary_reindex.py", str(prev_file))
    output_file = pathlib.Path(stdout)
    print(f"✅ 步驟3完成: {output_file}")
    return output_file

def run_4Condense(prev_file: pathlib.Path) -> pathlib.Path:
    """第4步：主題聚類"""
    print(f"🔄 步驟4: 主題聚類 - {prev_file}")
    stdout, stderr = run_subprocess_with_stdout("4Condense.py", str(prev_file))
    output_file = pathlib.Path(stdout)
    print(f"✅ 步驟4完成: {output_file}")
    return output_file

def run_pipeline_report(csv_file: pathlib.Path, num_initial: int = 3, chunk_size: int = 2) -> pathlib.Path:
    """第5步：生成報告"""
    print(f"🔄 步驟5: 生成報告 - {csv_file}")
    
    # pipeline_meeting_report.py 沒有純stdout輸出，需要推算輸出路徑
    csv_dir = csv_file.parent
    csv_grandparent = csv_dir.parent.parent  # 上兩層目錄
    output_dir = csv_grandparent
    
    cmd = [
        sys.executable, 
        "pipeline_meeting_report.py",
        "--csv", str(csv_file),
        "--output", str(output_dir),
        "--num-initial", str(num_initial),
        "--chunk-size", str(chunk_size)
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print("===== pipeline_meeting_report.py STDERR =====", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        sys.exit(result.returncode)
    
    # 查找生成的.md檔案
    md_files = list(output_dir.glob("*.md"))
    # 過濾掉系統檔案
    report_files = [f for f in md_files if f.name not in ['CLAUDE.md', 'PATENT_TECHNICAL_SPECS.md', 'README.md']]
    
    if not report_files:
        print(f"❌ 在 {output_dir} 未找到生成的報告檔案", file=sys.stderr)
        sys.exit(1)
    
    print(f"✅ 步驟5完成: 生成 {len(report_files)} 個報告檔案")
    for f in report_files:
        print(f"   📄 {f}")
    
    return output_dir  # 返回包含所有報告的目錄

def run_clean_md(report_dir: pathlib.Path) -> list:
    """第6步：清理報告"""
    print(f"🔄 步驟6: 清理報告 - {report_dir}")
    
    # 找到所有需要清理的.md檔案
    md_files = list(report_dir.glob("*.md"))
    # 過濾掉系統檔案
    report_files = [f for f in md_files if f.name not in ['CLAUDE.md', 'PATENT_TECHNICAL_SPECS.md', 'README.md']]
    
    cleaned_files = []
    
    for md_file in report_files:
        print(f"   🧹 清理: {md_file.name}")
        
        # clean_md.py 沒有純stdout，需要推算輸出路徑
        output_path = md_file.with_name(f"{md_file.stem}_cleaned.md")
        
        cmd = [
            sys.executable, 
            "clean_md.py",
            str(md_file),
            "-o", str(output_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"❌ 清理 {md_file} 失敗:", file=sys.stderr)
            print(result.stderr, file=sys.stderr)
            continue
        
        cleaned_files.append(output_path)
        print(f"   ✅ 已清理: {output_path}")
    
    print(f"✅ 步驟6完成: 清理 {len(cleaned_files)} 個檔案")
    return cleaned_files

def main():
    """主要執行流程"""
    start_time = time.time()
    print("🚀 開始執行完整會議處理流程")
    print("="*60)
    
    if len(sys.argv) != 2:
        print("用法：python integrated_main.py <逐字稿檔案路徑>")
        print("範例：python integrated_main.py /path/to/shorten.txt")
        sys.exit(1)
    
    src_file = sys.argv[1]
    
    if not os.path.exists(src_file):
        print(f"❌ 檔案不存在: {src_file}")
        sys.exit(1)
    
    print(f"📄 輸入檔案: {src_file}")
    print()
    
    try:
        # 步驟 1: 主題分段
        step1_out_dir = run_1topic_splitter(src_file)
        print()
        
        # 步驟 2: 生成摘要
        step2_out_file = run_2chunks_summary(step1_out_dir)
        print()
        
        # 步驟 3: 摘要重整
        step3_out_file = run_3brief_summary_reindex(step2_out_file)
        print()
        
        # 步驟 4: 主題聚類
        step4_out_file = run_4Condense(step3_out_file)
        print()
        
        # 步驟 5: 生成報告
        step5_out_dir = run_pipeline_report(step4_out_file)
        print()
        
        # 步驟 6: 清理報告
        final_files = run_clean_md(step5_out_dir)
        print()
        
        # 總結
        elapsed_time = time.time() - start_time
        print("="*60)
        print("🎉 完整流程執行完成!")
        print(f"⏱️  總耗時: {elapsed_time:.1f} 秒")
        print(f"📊 最終生成 {len(final_files)} 個清理後的報告:")
        
        for i, file in enumerate(final_files, 1):
            print(f"   {i}. {file}")
        
        print()
        print("💡 後續操作建議:")
        print("   • 檢查生成的報告內容")
        print("   • 如需進一步處理，可使用 enhanced_pipeline.py")
        print("   • 報告分析可使用 content_analyzer.py")
        
    except KeyboardInterrupt:
        print("\n⚠️  用戶中斷執行")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 執行過程中發生錯誤: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

def test_with_existing_data():
    """使用現有資料測試後半段流程"""
    print("🧪 測試模式：使用現有資料")
    
    # 使用你註解中的路徑
    existing_csv = "/home/henry/AuMeet_package/2025Feb_NSTM_meet_copy/shorten_topics/chunks_summaries_brief_output/chunks_summaries_brief_reindexed.csv"
    
    if not os.path.exists(existing_csv):
        print(f"❌ 測試檔案不存在: {existing_csv}")
        return
    
    try:
        # 從步驟4開始測試
        step4_out_file = run_4Condense(pathlib.Path(existing_csv))
        print()
        
        # 步驟5: 生成報告
        step5_out_dir = run_pipeline_report(step4_out_file)
        print()
        
        # 步驟6: 清理報告  
        final_files = run_clean_md(step5_out_dir)
        print()
        
        print("✅ 測試完成!")
        for f in final_files:
            print(f"   📄 {f}")
            
    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        test_with_existing_data()
    else:
        main()

#python main.py /home/henry/AuMeet_package/會議BSS/BSS.txt