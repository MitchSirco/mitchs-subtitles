import re
import argparse
from bisect import bisect_right

def time_str_to_seconds(time_str):
    parts = time_str.split(':')
    if len(parts) == 3:
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds_part = parts[2]
    elif len(parts) == 2:
        hours = 0
        minutes = int(parts[0])
        seconds_part = parts[1]
    else:
        hours = 0
        minutes = 0
        seconds_part = parts[0]
    
    if '.' in seconds_part:
        sec, ms = seconds_part.split('.')
        seconds = int(sec)
        ms = int(ms.ljust(2, '0')[:2])
    else:
        seconds = int(seconds_part)
        ms = 0
        
    return hours * 3600 + minutes * 60 + seconds + ms / 100.0

def seconds_to_ass_time(total_seconds):
    total_hundredths = round(total_seconds * 100)
    hours = total_hundredths // 360000
    remaining = total_hundredths % 360000
    minutes = remaining // 6000
    remaining_sec = remaining % 6000
    seconds = remaining_sec // 100
    hundredths = remaining_sec % 100
    return f"{hours}:{minutes:02d}:{seconds:02d}.{hundredths:02d}"

def interpolate_linear(p0, p1, t):
    return (
        p0[0] + (p1[0] - p0[0]) * t,
        p0[1] + (p1[1] - p0[1]) * t
    )

def interpolate_bezier(p0, p1, p2, p3, t):
    t2 = t * t
    t3 = t2 * t
    return (
        0.5 * (2 * p1[0] + t * (-p0[0] + p2[0]) + t2 * (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) + t3 * (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0])),
        0.5 * (2 * p1[1] + t * (-p0[1] + p2[1]) + t2 * (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) + t3 * (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]))
    )

def main():
    parser = argparse.ArgumentParser(description='Generate snake subtitles between specified points.')
    parser.add_argument('input_file', help='Input ASS subtitle file')
    parser.add_argument('output_file', help='Output ASS subtitle file')
    parser.add_argument('--interpolation', choices=['linear', 'bezier'], default='linear',
                        help='Interpolation method (linear or bezier)')
    parser.add_argument('--step', type=float, default=0.1,
                        help='Time step between points in seconds')
    parser.add_argument('--mode', choices=['A', 'B'], default='A',
                        help='Display mode: A=sequential, B=persistent')
    parser.add_argument('--duration', type=float, default=0.1,
                        help='Duration for each point in mode A')
    parser.add_argument('--text_mode', choices=['uniform', 'per_point'], default='uniform',
                        help='Text handling: uniform=first text for all, per_point=individual text')
    args = parser.parse_args()

    events = []
    other_lines = []
    anchor_times = []

    with open(args.input_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line.startswith("Dialogue: "):
                content = line[len("Dialogue: "):]
                parts = content.split(',', 9)
                if len(parts) < 10:
                    other_lines.append(line)
                    continue
                
                layer, start_str, end_str, style, name, marginL, marginR, marginV, effect, text = parts
                
                match = re.search(r'\\pos\((\d+),(\d+)\)', text)
                if match:
                    x, y = map(int, match.groups())
                    # Extract text without position tag
                    clean_text = re.sub(r'\\pos\(\d+,\d+\)', '', text).strip()
                    
                    start_sec = time_str_to_seconds(start_str)
                    end_sec = time_str_to_seconds(end_str)
                    
                    events.append({
                        'layer': layer,
                        'start_sec': start_sec,
                        'end_sec': end_sec,
                        'x': x, 'y': y,
                        'style': style,
                        'name': name,
                        'marginL': marginL,
                        'marginR': marginR,
                        'marginV': marginV,
                        'effect': effect,
                        'text': clean_text,
                        'original_line': line
                    })
                    anchor_times.append(start_sec)
                    continue
            other_lines.append(line)
    
    if len(events) < 2:
        print("Error: Need at least 2 anchor points")
        return
    
    events.sort(key=lambda e: e['start_sec'])
    anchor_times.sort()
    
    path = []
    total_start = events[0]['start_sec']
    total_end = events[-1]['start_sec']
    last_end_sec = events[-1]['end_sec']
    current_time = total_start
    
    while current_time <= total_end:
        # Find current segment
        segment_index = None
        for i in range(len(events) - 1):
            if events[i]['start_sec'] <= current_time <= events[i+1]['start_sec']:
                segment_index = i
                break
        
        if segment_index is None:
            segment_index = len(events) - 2
            
        if args.interpolation == 'linear':
            t0 = events[segment_index]['start_sec']
            t1 = events[segment_index+1]['start_sec']
            frac = (current_time - t0) / (t1 - t0) if t1 != t0 else 0.0
            x0, y0 = events[segment_index]['x'], events[segment_index]['y']
            x1, y1 = events[segment_index+1]['x'], events[segment_index+1]['y']
            x, y = interpolate_linear((x0, y0), (x1, y1), frac)
            path.append((current_time, round(x), round(y)))
            
        else:  # Bézier
            i = segment_index
            p0 = events[i-1] if i > 0 else events[i]
            p1 = events[i]
            p2 = events[i+1]
            p3 = events[i+2] if i+2 < len(events) else events[i+1]
            
            t0 = p1['start_sec']
            t1 = p2['start_sec']
            t_local = (current_time - t0) / (t1 - t0) if t1 != t0 else 0.0
            
            x, y = interpolate_bezier(
                (p0['x'], p0['y']),
                (p1['x'], p1['y']),
                (p2['x'], p2['y']),
                (p3['x'], p3['y']),
                t_local
            )
            path.append((current_time, round(x), round(y)))
        
        current_time += args.step

    new_events = []
    uniform_text = events[0]['text'] if events else ""
    
    for t, x, y in path:
        start_time = seconds_to_ass_time(t)
        
        # Determine text based on mode
        if args.text_mode == 'per_point':
            # Find closest anchor point
            idx = bisect_right(anchor_times, t) - 1
            text_content = events[max(0, idx)]['text'] if idx >= 0 else uniform_text
        else:
            text_content = uniform_text
        
        # Use style from nearest anchor point
        idx = bisect_right(anchor_times, t) - 1
        style_ref = events[max(0, idx)] if idx >= 0 else events[0]
        
        if args.mode == 'A':
            end_time = seconds_to_ass_time(t + args.duration)
        else:
            end_time = seconds_to_ass_time(last_end_sec)
        
        text_line = f"{{\\pos({x},{y})}}{text_content}"
        
        fields = [
            style_ref['layer'],
            start_time,
            end_time,
            style_ref['style'],
            style_ref['name'],
            style_ref['marginL'],
            style_ref['marginR'],
            style_ref['marginV'],
            style_ref['effect'],
            text_line
        ]
        new_events.append("Dialogue: " + ",".join(fields))
    
    with open(args.output_file, 'w', encoding='utf-8') as f:
        f.write("\n".join(other_lines))
        f.write("\n")
        f.write("\n".join(new_events))

if __name__ == "__main__":
    main()