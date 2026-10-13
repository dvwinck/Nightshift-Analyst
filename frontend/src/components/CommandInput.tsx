import { FormEvent, KeyboardEvent, useEffect, useRef, useState } from "react";

import { complete } from "../terminal/completion";
import { MessageView } from "../types";

type CommandInputProps = {
  inbox: MessageView[];
  disabled: boolean;
  onSubmit: (command: string) => void;
};

const CommandInput = ({ inbox, disabled, onSubmit }: CommandInputProps) => {
  const [value, setValue] = useState("");
  const [history, setHistory] = useState<string[]>([]);
  const [cursor, setCursor] = useState<number | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!disabled) inputRef.current?.focus();
  }, [disabled]);

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const command = value.trim();
    if (!command || disabled) return;
    setHistory((previous) => [...previous, command]);
    setCursor(null);
    setValue("");
    onSubmit(command);
  };

  const onKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Tab") {
      event.preventDefault();
      setValue((current) => complete(current, inbox));
    } else if (event.key === "ArrowUp" && history.length > 0) {
      event.preventDefault();
      const next = cursor === null ? history.length - 1 : Math.max(0, cursor - 1);
      setCursor(next);
      setValue(history[next]);
    } else if (event.key === "ArrowDown" && cursor !== null) {
      event.preventDefault();
      const next = cursor + 1;
      if (next >= history.length) {
        setCursor(null);
        setValue("");
      } else {
        setCursor(next);
        setValue(history[next]);
      }
    }
  };

  return (
    <form className="terminal-input" onSubmit={submit}>
      <label htmlFor="command" className="terminal-prompt">
        &gt;
      </label>
      <input
        id="command"
        ref={inputRef}
        type="text"
        value={value}
        onChange={(event) => setValue(event.target.value)}
        onKeyDown={onKeyDown}
        disabled={disabled}
        maxLength={200}
        autoComplete="off"
        autoCapitalize="off"
        spellCheck={false}
        placeholder={disabled ? "" : "type a command (help)"}
        aria-label="Command"
      />
    </form>
  );
};

export default CommandInput;
