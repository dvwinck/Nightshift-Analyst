import { MessageView } from "../types";

const COMMANDS = [
  "help",
  "status",
  "inbox",
  "read",
  "execute",
  "deny",
  "delay",
  "investigate",
  "wait",
  "clockout",
];
const TAKES_ARGUMENT = new Set(["read", "execute", "deny", "delay", "investigate", "wait"]);
const RESPONSE_VERBS = new Set(["execute", "deny", "delay", "investigate"]);

function commonPrefix(words: string[]): string {
  return words.reduce((prefix, word) => {
    let i = 0;
    while (i < prefix.length && i < word.length && prefix[i] === word[i]) i++;
    return prefix.slice(0, i);
  });
}

/** Tab-completion: returns the completed input, or the input unchanged when nothing applies. */
export function complete(input: string, inbox: MessageView[]): string {
  const trailingSpace = /\s$/.test(input);
  const parts = input.trim().toLowerCase().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return input;

  if (parts.length === 1 && !trailingSpace) {
    const matches = COMMANDS.filter((command) => command.startsWith(parts[0]));
    if (matches.length === 0) return input;
    if (matches.length === 1) {
      return TAKES_ARGUMENT.has(matches[0]) ? `${matches[0]} ` : matches[0];
    }
    return commonPrefix(matches);
  }

  const verb = parts[0];
  const wantsMessageId = verb === "read" || RESPONSE_VERBS.has(verb);
  const argumentIsBeingTyped = (parts.length === 1 && trailingSpace) || (parts.length === 2 && !trailingSpace);
  if (!wantsMessageId || !argumentIsBeingTyped) return input;

  const prefix = parts.length === 2 ? parts[1] : "";
  const candidates = inbox
    .filter((message) => verb === "read" || (message.read && message.verbs.some((v) => v.verb === verb)))
    .map((message) => message.id)
    .filter((id) => id.startsWith(prefix));
  if (candidates.length === 0) return input;
  const completed = candidates.length === 1 ? candidates[0] : commonPrefix(candidates);
  return `${verb} ${completed}`;
}
