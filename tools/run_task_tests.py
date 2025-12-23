#!/usr/bin/env python3
import json
import subprocess
import sys
import os
import base64

def run_test(command, input_str, expected, method, timeout=5):
    try:
        proc = subprocess.run(
            command,
            input=input_str,
            text=True,
            capture_output=True,
            timeout=timeout,
            shell=True
        )
        actual = proc.stdout.strip()
        stderr = proc.stderr

        if method == "exact":
            passed = actual == expected
        elif method == "contains":
            passed = expected in actual
        else:
            passed = False

        score = 1 if passed else 0
        output = actual
        if stderr and not passed:
            output += f"\nSTDERR: {stderr}"

        return {
            "name": "",
            "status": "pass" if passed else "fail",
            "score": score,
            "max_score": 1,
            "output": output
        }
    except subprocess.TimeoutExpired:
        return {"name": "", "status": "fail", "score": 0, "max_score": 1, "output": f"Timeout >{timeout}s"}
    except Exception as e:
        return {"name": "", "status": "fail", "score": 0, "max_score": 1, "output": f"Error: {e}"}

def main():
    if len(sys.argv) != 2:
        print("Usage: run_task_tests.py <task_id>")
        sys.exit(1)

    task_id = sys.argv[1]
    config_path = ".github/tasks.json"

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    task = None
    for t in config["tasks"]:
        if t["id"] == task_id:
            task = t
            break

    if not task:
        print(f"Task {task_id} not found in tasks.json")
        sys.exit(1)

    file_path = task["file"]
    max_score = task["max_score"]
    total_score = 0
    test_results = []

    # Проверка наличия файла
    if not os.path.exists(file_path):
        for test in task["tests"]:
            test_results.append({
                "name": test["name"],
                "status": "fail",
                "score": 0,
                "max_score": test["max_score"],
                "output": "Файл не найден"
            })
    else:
        # Проверка синтаксиса
        try:
            subprocess.run([sys.executable, "-m", "py_compile", file_path], check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            for test in task["tests"]:
                test_results.append({
                    "name": test["name"],
                    "status": "fail",
                    "score": 0,
                    "max_score": test["max_score"],
                    "output": f"SyntaxError\n{e.stderr.decode()}"
                })
        else:
            command = f"{sys.executable} {file_path}"
            for test in task["tests"]:
                res = run_test(
                    command=command,
                    input_str=test["input"],
                    expected=test["expected_output"],
                    method=test["comparison_method"],
                    timeout=5
                )
                res["name"] = test["name"]
                res["max_score"] = test["max_score"]
                res["score"] = res["score"] * test["max_score"]
                test_results.append(res)
                total_score += res["score"]

    # Формат, совместимый с autograding-io-grader@v1
    result = {
        "score": total_score,
        "max_score": max_score,
        "tests": test_results
    }

    encoded = base64.b64encode(json.dumps(result, ensure_ascii=False).encode("utf-8")).decode("utf-8")
    print(f"::set-output name=result::{encoded}")

if __name__ == "__main__":
    main()