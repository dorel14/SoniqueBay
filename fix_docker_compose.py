import sys

def main():
    with open('docker-compose.yml', 'r') as f:
        lines = f.readlines()

    # Find the start and end of the incorrectly placed taskiq-worker block
    start_idx = None
    end_idx = None
    for i, line in enumerate(lines):
        if '# === TASKIQ WORKER (NOUVEAU - Migration progressive depuis Celery) ===' in line:
            start_idx = i
        if '# === LLM SERVICE (KOBOLDCPP) ===' in line:
            end_idx = i
            break

    if start_idx is None or end_idx is None:
        print('Could not find taskiq-worker block')
        sys.exit(1)

    # Extract the block
    block = lines[start_idx:end_idx]  # This includes the comment line and the taskiq-worker service up to before the llm-service comment

    # Remove the block from the lines
    del lines[start_idx:end_idx]

    # Now, adjust the block to be a service: remove the indentation that was under the deploy section
    # Find the minimum indentation in the block (ignoring empty lines)
    min_indent = None
    for line in block:
        if line.strip() == '':
            continue
        indent_line = len(line) - len(line.lstrip())
        if min_indent is None or indent_line < min_indent:
            min_indent = indent_line

    if min_indent is not None:
        # Remove min_indent spaces from the beginning of each line
        block = [line[min_indent:] if line.strip() != '' else line for line in block]

    # Find the celery_beat service
    celery_beat_idx = None
    for i, line in enumerate(lines):
        if line.strip() == 'celery_beat:':
            celery_beat_idx = i
            break

    if celery_beat_idx is None:
        print('Could not find celery_beat service')
        sys.exit(1)

    # Find the end of the celery_beat service
    indent_celery_beat = len(lines[celery_beat_idx]) - len(lines[celery_beat_idx].lstrip())
    i = celery_beat_idx + 1
    while i < len(lines):
        if lines[i].strip() == '':
            i += 1
            continue
        current_indent = len(lines[i]) - len(lines[i].lstrip())
        if current_indent <= indent_celery_beat:
            break
        i += 1

    # Now, insert a blank line and then the block at position i
    lines.insert(i, '\n')
    for j, line in enumerate(block):
        lines.insert(i+1+j, line)

    # Write back
    with open('docker-compose.yml', 'w') as f:
        f.writelines(lines)

if __name__ == '__main__':
    main()
