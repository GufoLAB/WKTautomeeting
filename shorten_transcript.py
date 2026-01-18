# 2025/04/20 written by Grok 3 with the following prompt:
# 我要處理一份逐字稿，長相如下。請幫我寫一隻 Python 程式，把同一個人連續的發言合併：
# 只留下其一開始的時間標記，然後是合併連續發言的內容。請按照原來的順序呈現即可。
# 請注意同一個人連續的發言放在同一行，而不需要分行，但在即使放在同一行也要有適當的標點符號，以方便閱讀與理解。

# python shorten_transcript.py tmp/meetlingo0.txt > tmp/meetlingo1.txt
import re, sys
import os
    
def merge_consecutive_speech(transcript_lines, time_tag=False):
    merged_lines = []
    current_speaker = None
    current_time = None
    previous_end_time = None # added by Sam Tseng
    current_content = []

    for line in transcript_lines:
        # Match the line format using regex
        match = re.match(r'\[(.*?)\] (\[.*?\] )?\[(\d+:\d+:\d+ - \d+:\d+:\d+)\]\s*(.*)', line.strip())
        if not match:
            continue

        speaker, language, time_range, content = match.groups()
        start_time, end_time = time_range.split(' - ', 2)

        if speaker == current_speaker:
            # Same speaker, append content with proper punctuation
            if current_content and not current_content[-1].endswith(('，', '。', '？', '！')):
                current_content.append('，')
            current_content.append(content)
        else:
            # Different speaker, save previous and start new
            if current_speaker:
                msg = f'[{current_speaker}] {"".join(current_content)}'
                if time_tag:
                    msg = (f'[{current_speaker}] [{current_time} - {previous_end_time}] '
                           f'{"".join(current_content)}')
                # merged_lines.append(f'[{current_speaker}] [國語] '
                merged_lines.append(msg)
            current_speaker = speaker
            current_time = start_time
            current_content = [content]
        previous_end_time = end_time # 將目前的結束時間保存起來備用

    # Append the last speaker's content
    if current_speaker and current_content:
        msg = ""
        if time_tag:
            msg = f"[{current_time}] "
        # merged_lines.append(f'[{current_speaker}] [國語] [{current_time}] {"".join(current_content)}')
        merged_lines.append(f'[{current_speaker}] {msg}{"".join(current_content)}')

    return merged_lines


# Example usage
if __name__ == "__main__":
    input_file = sys.argv[1]
    with open(input_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    merged_lines = merge_consecutive_speech(lines)
    # merged_lines = DeepSeek_r1_70b_merge_speeches(lines)
    print("\n".join(merged_lines))
    output_file=os.path.splitext(input_file)[0]+'_shorten.txt'
    with open(output_file, 'w', encoding='utf-8') as fout:
        fout.write("\n".join(merged_lines))

# 範例使用
transcript_example = """
[Speaker_01] [國語] [0:05:00 - 0:05:02] Hello
[Speaker_01] [國語] [0:05:03 - 0:05:05] How are you?
[Speaker_02] [英語] [0:05:06 - 0:05:08] I'm good.
[Speaker_02] [英語] [0:05:06 - 0:05:08] And you?"""
result_example = """
[Speaker_01] [國語] [0:05:00 - 0:05:05] Hello. How are you?
[Speaker_02] [英語] [0:05:06 - 0:05:08] I'm good. And you?"""

