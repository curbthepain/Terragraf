"""
.scaffold/ml/models/terra_lm.py
TerraLM — A language model built around the Terragraf scaffold.

Deeply integrated with:
  - terra commands (init, route, lookup, gen, etc.)
  - .scaffold/ directory structure (routes, tables, headers, hooks)
  - Scaffold vocabulary (intents, error patterns, module deps)

The model tokenizes scaffold-native text (commands, routes, table entries,
header declarations) and learns to predict/generate within that domain.

Usage:
    from ml.models.terra_lm import TerraLM, TerraTokenizer

    tokenizer = TerraTokenizer()
    tokenizer.build_from_scaffold()  # reads .scaffold/ to build vocab

    model = TerraLM(vocab_size=tokenizer.vocab_size)
    model.to_device("cpu")
    model.summary()
"""

import torch
import torch.nn as nn
import math
import json
import re
from pathlib import Path
from collections import Counter
from .base_model import ScaffoldModel


# ─── Tokenizer ──────────────────────────────────────────────────────────

class TerraTokenizer:
    """Tokenizer built from the scaffold's own vocabulary.

    Ingests routes, tables, headers, commands, and config to build
    a domain-specific token set. Supports special tokens for scaffold
    constructs like [CMD], [ROUTE], [TABLE], [HEADER], [PATH].
    """

    SPECIAL_TOKENS = [
        "[PAD]", "[UNK]", "[BOS]", "[EOS]",
        "[CMD]", "[ROUTE]", "[TABLE]", "[HEADER]",
        "[PATH]", "[ERROR]", "[FIX]", "[MODULE]",
        "[INTENT]", "[TARGET]", "[SEP]",
    ]

    def __init__(self):
        self.token_to_id = {}
        self.id_to_token = {}
        self.vocab_size = 0
        self._built = False

    def build_from_scaffold(self, scaffold_dir=".scaffold"):
        """Scan the scaffold directory and build vocabulary."""
        root = Path(scaffold_dir)
        corpus = []

        # Collect text from routes
        for f in sorted(root.glob("routes/*.route")):
            corpus.extend(self._parse_route_file(f))

        # Collect text from tables
        for f in sorted(root.glob("tables/*.table")):
            corpus.extend(self._parse_table_file(f))

        # Collect text from headers
        for f in sorted(root.glob("headers/*.h")):
            corpus.extend(self._parse_header_file(f))

        # Collect terra commands
        corpus.extend(self._parse_terra_commands())

        # Collect manifest keys
        manifest = root / "MANIFEST.toml"
        if manifest.exists():
            corpus.extend(self._parse_toml_keys(manifest))

        # Build vocab from corpus
        self._build_vocab(corpus)
        self._built = True
        return self

    def _parse_route_file(self, path):
        """Extract intents and targets from .route files."""
        tokens = []
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "->" in line:
                intent, target = line.split("->", 1)
                tokens.extend(self._tokenize_text(intent.strip()))
                tokens.extend(self._tokenize_text(target.strip()))
            else:
                tokens.extend(self._tokenize_text(line))
        return tokens

    def _parse_table_file(self, path):
        """Extract patterns, causes, and fixes from .table files."""
        tokens = []
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            for part in re.split(r"[|→\->]", line):
                tokens.extend(self._tokenize_text(part.strip()))
        return tokens

    def _parse_header_file(self, path):
        """Extract declarations from .h files."""
        tokens = []
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("//"):
                continue
            tokens.extend(self._tokenize_text(line))
        return tokens

    def _parse_terra_commands(self):
        """Hardcoded terra command vocabulary."""
        commands = [
            "init", "status", "help", "route", "lookup", "pattern", "dep",
            "gen", "module", "model", "shader", "hook", "enter", "commit",
            "generate", "instance", "imgui", "build", "run", "math", "nodes",
            "viz", "spectrogram", "heatmap", "stream", "3d", "volume", "mesh",
            "queue", "add", "sharpen", "tune", "show", "load", "zone", "set",
            "axes", "directive", "promise", "mode", "check", "can", "app",
            "eval", "linalg", "stats", "offscreen", "bridge",
        ]
        return commands

    def _parse_toml_keys(self, path):
        """Extract keys and values from TOML-like config."""
        tokens = []
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("["):
                if line.startswith("["):
                    section = line.strip("[]")
                    tokens.extend(self._tokenize_text(section))
                continue
            if "=" in line:
                key, val = line.split("=", 1)
                tokens.extend(self._tokenize_text(key.strip()))
                val = val.strip().strip('"').strip("'")
                if val and val not in ("true", "false"):
                    tokens.extend(self._tokenize_text(val))
        return tokens

    def _tokenize_text(self, text):
        """Split text into word-level tokens."""
        text = text.lower()
        # Split on whitespace, punctuation, underscores, slashes, dots
        parts = re.split(r"[\s_/.\-,;:=|()\"'\[\]{}]+", text)
        return [p for p in parts if p]

    def _build_vocab(self, corpus):
        """Build token-to-id mapping from corpus + special tokens."""
        counts = Counter(corpus)
        # Start with special tokens
        vocab = list(self.SPECIAL_TOKENS)
        # Add corpus tokens sorted by frequency
        for token, _ in counts.most_common():
            if token not in vocab:
                vocab.append(token)
        self.token_to_id = {t: i for i, t in enumerate(vocab)}
        self.id_to_token = {i: t for t, i in self.token_to_id.items()}
        self.vocab_size = len(vocab)

    def encode(self, text, max_len=None):
        """Encode text to token ids."""
        tokens = self._tokenize_text(text)
        ids = [self.token_to_id.get("[BOS]", 0)]
        for t in tokens:
            ids.append(self.token_to_id.get(t, self.token_to_id["[UNK]"]))
        ids.append(self.token_to_id.get("[EOS]", 0))
        if max_len:
            pad_id = self.token_to_id["[PAD]"]
            ids = ids[:max_len]
            ids += [pad_id] * (max_len - len(ids))
        return ids

    def decode(self, ids):
        """Decode token ids back to text."""
        tokens = []
        for i in ids:
            tok = self.id_to_token.get(i, "[UNK]")
            if tok in ("[PAD]", "[BOS]", "[EOS]"):
                continue
            tokens.append(tok)
        return " ".join(tokens)

    def encode_command(self, command_str):
        """Encode a terra command with [CMD] prefix."""
        cmd_id = self.token_to_id["[CMD]"]
        inner = self.encode(command_str)
        return [inner[0], cmd_id] + inner[1:]  # [BOS] [CMD] ...tokens... [EOS]

    def encode_route(self, intent, target=None):
        """Encode a route query with [INTENT] and [TARGET] markers."""
        ids = [self.token_to_id["[BOS]"], self.token_to_id["[ROUTE]"]]
        ids.append(self.token_to_id["[INTENT]"])
        for t in self._tokenize_text(intent):
            ids.append(self.token_to_id.get(t, self.token_to_id["[UNK]"]))
        if target:
            ids.append(self.token_to_id["[TARGET]"])
            for t in self._tokenize_text(target):
                ids.append(self.token_to_id.get(t, self.token_to_id["[UNK]"]))
        ids.append(self.token_to_id["[EOS]"])
        return ids

    def save(self, path):
        """Save tokenizer vocab to JSON."""
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump({"token_to_id": self.token_to_id, "vocab_size": self.vocab_size}, f)

    def load(self, path):
        """Load tokenizer vocab from JSON."""
        with open(path) as f:
            data = json.load(f)
        self.token_to_id = data["token_to_id"]
        self.id_to_token = {int(i): t for t, i in self.token_to_id.items()}
        self.vocab_size = data["vocab_size"]
        self._built = True
        return self


# ─── Model ──────────────────────────────────────────────────────────────

class TerraLMBlock(nn.Module):
    """Transformer block with causal self-attention for autoregressive LM."""

    def __init__(self, d_model, n_heads, d_ff, dropout=0.1):
        super().__init__()
        self.attn = nn.MultiheadAttention(d_model, n_heads, dropout=dropout, batch_first=True)
        self.norm1 = nn.LayerNorm(d_model)
        self.norm2 = nn.LayerNorm(d_model)
        self.ffn = nn.Sequential(
            nn.Linear(d_model, d_ff),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(d_ff, d_model),
            nn.Dropout(dropout),
        )

    def forward(self, x, causal_mask=None):
        attended, _ = self.attn(x, x, x, attn_mask=causal_mask, is_causal=causal_mask is None)
        x = self.norm1(x + attended)
        x = self.norm2(x + self.ffn(x))
        return x


class TerraLM(ScaffoldModel):
    """Autoregressive language model for the Terragraf scaffold domain.

    Architecture:
        Token embedding + positional encoding → N transformer blocks → LM head

    The model operates over scaffold-native tokens: commands, routes,
    table entries, header declarations, file paths, error patterns.

    Args:
        vocab_size:   Number of tokens (from TerraTokenizer)
        d_model:      Embedding dimension
        n_heads:      Attention heads per block
        n_layers:     Number of transformer blocks
        d_ff:         Feed-forward inner dimension
        max_seq_len:  Maximum sequence length
        dropout:      Dropout rate
    """

    def __init__(self, vocab_size, d_model=256, n_heads=4, n_layers=4,
                 d_ff=512, max_seq_len=256, dropout=0.1):
        super().__init__()
        self.d_model = d_model
        self.max_seq_len = max_seq_len

        self.token_emb = nn.Embedding(vocab_size, d_model, padding_idx=0)
        self.pos_emb = nn.Embedding(max_seq_len, d_model)
        self.drop = nn.Dropout(dropout)

        self.blocks = nn.ModuleList([
            TerraLMBlock(d_model, n_heads, d_ff, dropout)
            for _ in range(n_layers)
        ])

        self.ln_f = nn.LayerNorm(d_model)
        self.lm_head = nn.Linear(d_model, vocab_size, bias=False)

        # Weight tying: share embedding and output weights
        self.lm_head.weight = self.token_emb.weight

        self._init_weights()

    def _init_weights(self):
        for p in self.parameters():
            if p.dim() > 1:
                nn.init.xavier_uniform_(p)

    def forward(self, input_ids, targets=None):
        """Forward pass. Returns logits, and loss if targets provided.

        Args:
            input_ids: (batch, seq_len) token ids
            targets:   (batch, seq_len) target token ids for next-token prediction

        Returns:
            logits: (batch, seq_len, vocab_size)
            loss:   scalar cross-entropy loss (only if targets given)
        """
        B, T = input_ids.shape
        assert T <= self.max_seq_len, f"Sequence length {T} exceeds max {self.max_seq_len}"

        positions = torch.arange(T, device=input_ids.device).unsqueeze(0)
        x = self.drop(self.token_emb(input_ids) + self.pos_emb(positions))

        # Causal mask: upper triangular = -inf
        causal_mask = nn.Transformer.generate_square_subsequent_mask(T, device=input_ids.device)

        for block in self.blocks:
            x = block(x, causal_mask)

        x = self.ln_f(x)
        logits = self.lm_head(x)

        loss = None
        if targets is not None:
            loss = nn.functional.cross_entropy(
                logits.view(-1, logits.size(-1)),
                targets.view(-1),
                ignore_index=0,  # ignore [PAD]
            )

        return logits, loss

    @torch.no_grad()
    def generate(self, input_ids, max_new_tokens=50, temperature=0.8, top_k=20):
        """Autoregressive generation from a prompt.

        Args:
            input_ids:      (1, seq_len) prompt token ids
            max_new_tokens: How many tokens to generate
            temperature:    Sampling temperature (lower = more deterministic)
            top_k:          Only sample from top-k most likely tokens

        Returns:
            (1, seq_len + max_new_tokens) generated token ids
        """
        self.eval()
        for _ in range(max_new_tokens):
            # Crop to max_seq_len if needed
            idx_cond = input_ids[:, -self.max_seq_len:]
            logits, _ = self.forward(idx_cond)
            logits = logits[:, -1, :] / temperature

            # Top-k filtering
            if top_k > 0:
                topk_vals, _ = torch.topk(logits, top_k)
                logits[logits < topk_vals[:, [-1]]] = float("-inf")

            probs = torch.softmax(logits, dim=-1)
            next_id = torch.multinomial(probs, num_samples=1)
            input_ids = torch.cat([input_ids, next_id], dim=1)

            # Stop on [EOS]
            if next_id.item() == 3:  # [EOS] = id 3
                break

        return input_ids


# ─── Dataset ────────────────────────────────────────────────────────────

class TerraCorpus:
    """Builds a training corpus from the scaffold's own content.

    Generates next-token prediction sequences from:
      - Route mappings:  "[ROUTE] [INTENT] fix bug [TARGET] routes/bugs.route"
      - Table lookups:   "[TABLE] [ERROR] ModuleNotFoundError [FIX] pip install ..."
      - Command docs:    "[CMD] terra route intent -> location"
      - Header decls:    "[HEADER] [MODULE] math -> compute/math/"
    """

    def __init__(self, tokenizer):
        self.tokenizer = tokenizer
        self.sequences = []

    def build(self, scaffold_dir=".scaffold"):
        """Parse scaffold content into training sequences."""
        root = Path(scaffold_dir)

        # Route sequences
        for f in sorted(root.glob("routes/*.route")):
            self._add_routes(f)

        # Table sequences
        for f in sorted(root.glob("tables/*.table")):
            self._add_tables(f)

        # Header sequences
        for f in sorted(root.glob("headers/*.h")):
            self._add_headers(f)

        # Command sequences
        self._add_commands()

        return self

    def _add_routes(self, path):
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "->" in line:
                intent, target = line.split("->", 1)
                ids = self.tokenizer.encode_route(intent.strip(), target.strip())
                self.sequences.append(ids)

    def _add_tables(self, path):
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "|" in line:
                parts = [p.strip() for p in line.split("|")]
                ids = [self.tokenizer.token_to_id["[BOS]"],
                       self.tokenizer.token_to_id["[TABLE]"]]
                for i, part in enumerate(parts):
                    for t in self.tokenizer._tokenize_text(part):
                        ids.append(self.tokenizer.token_to_id.get(t, 1))
                    if i < len(parts) - 1:
                        ids.append(self.tokenizer.token_to_id["[SEP]"])
                ids.append(self.tokenizer.token_to_id["[EOS]"])
                self.sequences.append(ids)

    def _add_headers(self, path):
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("//") or line.startswith("---"):
                continue
            ids = [self.tokenizer.token_to_id["[BOS]"],
                   self.tokenizer.token_to_id["[HEADER]"]]
            for t in self.tokenizer._tokenize_text(line):
                ids.append(self.tokenizer.token_to_id.get(t, 1))
            ids.append(self.tokenizer.token_to_id["[EOS]"])
            self.sequences.append(ids)

    def _add_commands(self):
        cmds = [
            "terra init wire hooks check env",
            "terra status show platforms runtimes",
            "terra route intent find where to work",
            "terra lookup error find known fix",
            "terra pattern name show design pattern",
            "terra dep module show dependencies",
            "terra gen module name generate module",
            "terra gen model name generate pytorch model",
            "terra gen shader name generate compute shader",
            "terra hook enter run on session start",
            "terra hook commit run around commits",
            "terra imgui build cmake make",
            "terra imgui run launch viewer",
            "terra viz spectrogram render fft visual",
            "terra viz heatmap render 2d colormap",
            "terra viz stream realtime scrolling chart",
            "terra math eval expression evaluate",
            "terra math linalg linear algebra",
            "terra math stats statistics",
            "terra queue show task queue",
            "terra queue add task add to queue",
            "terra sharpen self sharpening analytics",
            "terra tune thematic calibration profiles",
            "terra mode detect ci or app",
            "terra app launch qt container",
        ]
        for cmd in cmds:
            ids = self.tokenizer.encode_command(cmd)
            self.sequences.append(ids)

    def as_tensor_pairs(self, max_len=64):
        """Convert sequences to (input, target) tensor pairs for training.

        For each sequence, input = seq[:-1], target = seq[1:] (next-token).
        """
        inputs, targets = [], []
        pad_id = self.tokenizer.token_to_id["[PAD]"]

        for seq in self.sequences:
            if len(seq) < 3:
                continue
            seq = seq[:max_len + 1]
            inp = seq[:-1]
            tgt = seq[1:]
            # Pad
            while len(inp) < max_len:
                inp.append(pad_id)
                tgt.append(pad_id)
            inputs.append(inp)
            targets.append(tgt)

        return torch.tensor(inputs, dtype=torch.long), torch.tensor(targets, dtype=torch.long)
