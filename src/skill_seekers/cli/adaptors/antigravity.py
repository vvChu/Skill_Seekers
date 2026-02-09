#!/usr/bin/env python3
"""
Google Antigravity Adaptor

Implements platform-specific handling for Google Antigravity skills.
Antigravity is an agent-first AI IDE powered by Gemini 3, supporting autonomous
agents with multi-surface workflows (editor, terminal, browser).

Uses Gemini Files API for upload and Gemini 3 for enhancement.
"""

import json
import os
import tarfile
from pathlib import Path
from typing import Any

from .base import SkillAdaptor, SkillMetadata


class AntigravityAdaptor(SkillAdaptor):
    """
    Google Antigravity platform adaptor.

    Antigravity is an agent-first IDE that uses autonomous agents to plan, execute,
    and verify coding tasks. Skills are lightweight markdown-based extensions that
    equip agents with specialized knowledge.

    Handles:
    - Agent-first markdown format with specialized sections
    - tar.gz packaging for Antigravity format
    - Upload to Google AI Studio / Files API (same as Gemini)
    - AI enhancement using Gemini 3 (agent-consumable documentation)
    """

    PLATFORM = "antigravity"
    PLATFORM_NAME = "Google Antigravity"
    DEFAULT_API_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/files"

    def format_skill_md(self, skill_dir: Path, metadata: SkillMetadata) -> str:
        """
        Format SKILL.md for Antigravity's agent-first paradigm.

        Antigravity requires agent-consumable documentation with:
        - NO YAML frontmatter (plain markdown like Gemini)
        - "Agent Instructions" section for multi-surface guidance
        - "Verification Steps" section for artifact validation
        - "Artifacts" section describing expected outputs

        Args:
            skill_dir: Path to skill directory
            metadata: Skill metadata

        Returns:
            Formatted SKILL.md content (plain markdown, agent-first)
        """
        # Read existing content (if any)
        existing_content = self._read_existing_content(skill_dir)

        # If existing content is substantial, use it as base
        if existing_content and len(existing_content) > 100:
            content_body = existing_content
        else:
            # Generate agent-first content
            content_body = f"""# {metadata.name.title()} Documentation

**Description:** {metadata.description}

## Agent Instructions

This skill equips autonomous agents with specialized knowledge about {metadata.name}.

**Multi-Surface Usage:**
- **Editor**: Use for code completion, refactoring, and navigation
- **Terminal**: Execute commands and run tests
- **Browser**: Access documentation and examples

**When to Use:**
- Working with {metadata.name} codebase or documentation
- Need guidance on best practices and patterns
- Implementing features using {metadata.name}

## Quick Reference

{self._extract_quick_reference(skill_dir)}

## Verification Steps

Agents can validate their work using these steps:

1. **Code Quality**: Ensure code follows {metadata.name} conventions
2. **Tests**: Run test suite and verify all tests pass
3. **Documentation**: Check that changes are properly documented
4. **Examples**: Verify examples work as expected

## Artifacts

Expected agent outputs when using this skill:

- **Task Lists**: Breakdown of work items
- **Implementation Plans**: Step-by-step approach
- **Code Changes**: Diffs showing modifications
- **Test Results**: Output from test execution
- **Documentation Updates**: Changes to docs

## Table of Contents

{self._generate_toc(skill_dir)}

## Documentation Structure

This skill contains comprehensive documentation organized into categorized reference files.

### Available References

{self._generate_toc(skill_dir)}

## How to Use This Skill

When working with {metadata.name}:
1. Reference specific topics or features needed
2. Agents will automatically consult documentation sections
3. Receive detailed guidance with code examples
4. Verify outputs using artifact-based validation

## Navigation

See the references directory for complete documentation with examples and best practices.
"""

        # Return plain markdown (NO frontmatter, agent-first format)
        return content_body

    def package(
        self,
        skill_dir: Path,
        output_path: Path,
        enable_chunking: bool = False,
        chunk_max_tokens: int = 512,
        preserve_code_blocks: bool = True,
    ) -> Path:
        """
        Package skill into tar.gz file for Antigravity.

        Creates Antigravity-specific structure:
        - agent_instructions.md (main SKILL.md, renamed for Antigravity convention)
        - references/*.md (reference docs)
        - antigravity_metadata.json (skill metadata with agent configuration)

        Args:
            skill_dir: Path to skill directory
            output_path: Output path/filename for tar.gz
            enable_chunking: Enable chunking (ignored for Antigravity)
            chunk_max_tokens: Max tokens per chunk (ignored)
            preserve_code_blocks: Preserve code blocks (ignored)

        Returns:
            Path to created tar.gz file
        """
        skill_dir = Path(skill_dir)

        # Determine output filename
        if output_path.is_dir() or str(output_path).endswith("/"):
            output_path = Path(output_path) / f"{skill_dir.name}-antigravity.tar.gz"
        elif not str(output_path).endswith(".tar.gz"):
            # Replace .zip with .tar.gz if needed
            output_str = str(output_path).replace(".zip", ".tar.gz")
            if not output_str.endswith(".tar.gz"):
                output_str += ".tar.gz"
            output_path = Path(output_str)

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Create tar.gz file
        with tarfile.open(output_path, "w:gz") as tar:
            # Add SKILL.md as agent_instructions.md (Antigravity convention)
            skill_md = skill_dir / "SKILL.md"
            if skill_md.exists():
                tar.add(skill_md, arcname="agent_instructions.md")

            # Add references directory (if exists)
            refs_dir = skill_dir / "references"
            if refs_dir.exists():
                for ref_file in refs_dir.rglob("*"):
                    if ref_file.is_file() and not ref_file.name.startswith("."):
                        arcname = ref_file.relative_to(skill_dir)
                        tar.add(ref_file, arcname=str(arcname))

            # Create and add Antigravity-specific metadata file
            metadata = {
                "platform": "antigravity",
                "name": skill_dir.name,
                "version": "1.0.0",
                "created_with": "skill-seekers",
                "agent_config": {
                    "surfaces": ["editor", "terminal", "browser"],
                    "parallel_capable": True,
                    "verification": "artifact-based",
                },
            }

            # Write metadata to temp file and add to archive
            import tempfile

            with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
                json.dump(metadata, tmp, indent=2)
                tmp_path = tmp.name

            try:
                tar.add(tmp_path, arcname="antigravity_metadata.json")
            finally:
                os.unlink(tmp_path)

        return output_path

    def upload(self, package_path: Path, api_key: str, **_kwargs) -> dict[str, Any]:
        """
        Upload skill tar.gz to Gemini Files API.

        Antigravity uses the same backend as Gemini (Google AI Studio).

        Args:
            package_path: Path to skill tar.gz file
            api_key: Google API key (GOOGLE_API_KEY)
            **kwargs: Additional arguments

        Returns:
            Dictionary with upload result
        """
        # Validate package file FIRST
        package_path = Path(package_path)
        if not package_path.exists():
            return {
                "success": False,
                "skill_id": None,
                "url": None,
                "message": f"File not found: {package_path}",
            }

        if package_path.suffix != ".gz":
            return {
                "success": False,
                "skill_id": None,
                "url": None,
                "message": f"Not a tar.gz file: {package_path}",
            }

        # Check for google-generativeai library
        try:
            import google.generativeai as genai
        except ImportError:
            return {
                "success": False,
                "skill_id": None,
                "url": None,
                "message": "google-generativeai library not installed. Run: pip install google-generativeai",
            }

        # Configure Gemini
        try:
            genai.configure(api_key=api_key)

            # Extract tar.gz to temp directory
            import tempfile

            with tempfile.TemporaryDirectory() as temp_dir:
                # Extract archive
                with tarfile.open(package_path, "r:gz") as tar:
                    tar.extractall(temp_dir)

                temp_path = Path(temp_dir)

                # Upload main file (agent_instructions.md)
                main_file = temp_path / "agent_instructions.md"
                if not main_file.exists():
                    return {
                        "success": False,
                        "skill_id": None,
                        "url": None,
                        "message": "Invalid package: agent_instructions.md not found",
                    }

                # Upload to Files API
                uploaded_file = genai.upload_file(
                    path=str(main_file), display_name=f"{package_path.stem}_instructions"
                )

                # Upload reference files (if any)
                refs_dir = temp_path / "references"
                uploaded_refs = []
                if refs_dir.exists():
                    for ref_file in refs_dir.glob("*.md"):
                        ref_uploaded = genai.upload_file(
                            path=str(ref_file), display_name=f"{package_path.stem}_{ref_file.stem}"
                        )
                        uploaded_refs.append(ref_uploaded.name)

            return {
                "success": True,
                "skill_id": uploaded_file.name,
                "url": f"https://aistudio.google.com/app/files/{uploaded_file.name}",
                "message": f"Skill uploaded to Google AI Studio for Antigravity ({len(uploaded_refs) + 1} files)",
            }

        except Exception as e:
            return {
                "success": False,
                "skill_id": None,
                "url": None,
                "message": f"Upload failed: {str(e)}",
            }

    def validate_api_key(self, api_key: str) -> bool:
        """
        Validate Google API key format.

        Args:
            api_key: API key to validate

        Returns:
            True if key starts with 'AIza'
        """
        return api_key.strip().startswith("AIza")

    def get_env_var_name(self) -> str:
        """
        Get environment variable name for Google API key.

        Returns:
            'GOOGLE_API_KEY' (shared with Gemini)
        """
        return "GOOGLE_API_KEY"

    def supports_enhancement(self) -> bool:
        """
        Antigravity supports AI enhancement via Gemini 3.

        Returns:
            True
        """
        return True

    def enhance(self, skill_dir: Path, api_key: str) -> bool:
        """
        Enhance SKILL.md using Gemini 3 API with Antigravity-specific prompt.

        Emphasizes agent-consumable documentation with multi-surface workflow guidance
        and artifact verification patterns.

        Args:
            skill_dir: Path to skill directory
            api_key: Google API key

        Returns:
            True if enhancement succeeded
        """
        # Check for google-generativeai library
        try:
            import google.generativeai as genai
        except ImportError:
            print("❌ Error: google-generativeai package not installed")
            print("Install with: pip install google-generativeai")
            return False

        skill_dir = Path(skill_dir)
        references_dir = skill_dir / "references"
        skill_md_path = skill_dir / "SKILL.md"

        # Read reference files
        print("📖 Reading reference documentation...")
        references = self._read_reference_files(references_dir)

        if not references:
            print("❌ No reference files found to analyze")
            return False

        print(f"  ✓ Read {len(references)} reference files")
        total_size = sum(len(c) for c in references.values())
        print(f"  ✓ Total size: {total_size:,} characters\n")

        # Read current SKILL.md
        current_skill_md = None
        if skill_md_path.exists():
            current_skill_md = skill_md_path.read_text(encoding="utf-8")
            print(f"  ℹ Found existing SKILL.md ({len(current_skill_md)} chars)")
        else:
            print("  ℹ No existing SKILL.md, will create new one")

        # Build Antigravity-specific enhancement prompt
        prompt = self._build_enhancement_prompt(skill_dir.name, references, current_skill_md)

        print("\n🤖 Asking Gemini 3 to enhance SKILL.md for Antigravity agents...")
        print(f"   Input: {len(prompt):,} characters")

        try:
            genai.configure(api_key=api_key)

            model = genai.GenerativeModel("gemini-2.0-flash-exp")

            response = model.generate_content(prompt)

            enhanced_content = response.text
            print(f"  ✓ Generated enhanced SKILL.md ({len(enhanced_content)} chars)\n")

            # Backup original
            if skill_md_path.exists():
                backup_path = skill_md_path.with_suffix(".md.backup")
                skill_md_path.rename(backup_path)
                print(f"  💾 Backed up original to: {backup_path.name}")

            # Save enhanced version
            skill_md_path.write_text(enhanced_content, encoding="utf-8")
            print("  ✅ Saved enhanced SKILL.md for Antigravity")

            return True

        except Exception as e:
            print(f"❌ Error calling Gemini API: {e}")
            return False

    def _read_reference_files(
        self, references_dir: Path, max_chars: int = 200000
    ) -> dict[str, str]:
        """
        Read reference markdown files from skill directory.

        Args:
            references_dir: Path to references directory
            max_chars: Maximum total characters to read

        Returns:
            Dictionary mapping filename to content
        """
        if not references_dir.exists():
            return {}

        references = {}
        total_chars = 0

        # Read all .md files
        for ref_file in sorted(references_dir.glob("*.md")):
            if total_chars >= max_chars:
                break

            try:
                content = ref_file.read_text(encoding="utf-8")
                # Limit individual file size
                if len(content) > 30000:
                    content = content[:30000] + "\n\n...(truncated)"

                references[ref_file.name] = content
                total_chars += len(content)

            except Exception as e:
                print(f"  ⚠️  Could not read {ref_file.name}: {e}")

        return references

    def _build_enhancement_prompt(
        self, skill_name: str, references: dict[str, str], current_skill_md: str = None
    ) -> str:
        """
        Build Gemini API prompt for Antigravity-specific enhancement.

        Args:
            skill_name: Name of the skill
            references: Dictionary of reference content
            current_skill_md: Existing SKILL.md content (optional)

        Returns:
            Enhancement prompt for Gemini
        """
        prompt = f"""You are enhancing a skill's documentation for use with Google Antigravity - an agent-first AI IDE powered by Gemini 3. This skill is about: {skill_name}

I've scraped documentation and organized it into reference files. Your job is to create EXCELLENT agent-consumable documentation that autonomous agents can use effectively across multiple surfaces (editor, terminal, browser).

CURRENT DOCUMENTATION:
{"```markdown" if current_skill_md else "(none - create from scratch)"}
{current_skill_md or "No existing documentation"}
{"```" if current_skill_md else ""}

REFERENCE DOCUMENTATION:
"""

        for filename, content in references.items():
            prompt += f"\n\n## {filename}\n```markdown\n{content[:30000]}\n```\n"

        prompt += """

YOUR TASK:
Create enhanced AGENT-FIRST documentation for Google Antigravity that includes:

1. **Clear Agent Instructions** - Guide autonomous agents on:
   - When to use this skill (task types, contexts)
   - Multi-surface workflows (editor, terminal, browser)
   - How to navigate and use the documentation effectively

2. **Excellent Quick Reference section** - Extract 5-10 of the BEST, most practical code examples
   - Choose SHORT, clear examples that demonstrate common tasks agents will perform
   - Include both simple and intermediate examples
   - Annotate examples with clear descriptions
   - Use proper language tags (cpp, python, javascript, json, etc.)

3. **Verification Steps** - Help agents validate their work:
   - Code quality checks
   - Testing approaches
   - Documentation requirements
   - Examples validation

4. **Artifacts Section** - Describe expected agent outputs:
   - Task lists and implementation plans
   - Code changes (diffs)
   - Test results
   - Documentation updates

5. **Table of Contents** - List all reference sections for easy navigation

6. **Practical usage guidance** - Help agents navigate and use the documentation effectively

7. **Key Concepts section** (if applicable) - Explain core concepts in agent-consumable format

8. **DO NOT use YAML frontmatter** - This is plain markdown for agent consumption

IMPORTANT FOR AGENT-FIRST FORMAT:
- Extract REAL examples from the reference docs, don't make them up
- Prioritize SHORT, clear examples (5-20 lines max) that agents can quickly understand
- Make it actionable and practical for autonomous agents
- Structure content so agents can parse and execute effectively
- Include multi-surface workflow guidance (editor, terminal, browser)
- Add artifact verification patterns agents can follow
- Use clean markdown formatting
- Keep code examples properly formatted with language tags
- NO YAML frontmatter (no --- blocks)
- Focus on agent consumability over human readability

OUTPUT:
Return ONLY the complete markdown content, starting with the main title (#).
"""

        return prompt
