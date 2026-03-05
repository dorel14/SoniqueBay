"""
Tests for artist name capitalization fix in entity_manager.

This module tests the proper_case_artist_name function and its integration
with the artist creation process.
"""

import pytest
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from backend_worker.services.entity_manager import proper_case_artist_name


class TestProperCaseArtistName:
    """Test cases for the proper_case_artist_name function."""
    
    def test_simple_lowercase_name(self):
        """Test simple lowercase names are properly capitalized."""
        assert proper_case_artist_name("philippe timsit") == "Philippe Timsit"
        assert proper_case_artist_name("john doe") == "John Doe"
        assert proper_case_artist_name("jane smith") == "Jane Smith"
    
    def test_already_proper_case(self):
        """Test names already in proper case remain unchanged."""
        assert proper_case_artist_name("Philippe Timsit") == "Philippe Timsit"
        assert proper_case_artist_name("John Doe") == "John Doe"
        assert proper_case_artist_name("AC/DC") == "AC/DC"
    
    def test_mixed_case(self):
        """Test mixed case names are normalized."""
        assert proper_case_artist_name("pHiLiPpE tImSiT") == "Philippe Timsit"
        assert proper_case_artist_name("jOhN dOe") == "John Doe"
    
    def test_special_cases_acdc(self):
        """Test AC/DC special case handling."""
        assert proper_case_artist_name("ac/dc") == "AC/DC"
        assert proper_case_artist_name("AC/DC") == "AC/DC"
        assert proper_case_artist_name("ac-dc") == "AC-DC"
    
    def test_dj_prefix(self):
        """Test DJ prefix handling."""
        assert proper_case_artist_name("dj shadow") == "DJ Shadow"
        assert proper_case_artist_name("DJ Shadow") == "DJ Shadow"
        assert proper_case_artist_name("dj tiesto") == "DJ Tiesto"
    
    def test_mc_prefix(self):
        """Test MC prefix handling."""
        assert proper_case_artist_name("mc hammer") == "MC Hammer"
        assert proper_case_artist_name("MC Hammer") == "MC Hammer"
    
    def test_rnb_variants(self):
        """Test R&B genre handling."""
        assert proper_case_artist_name("r&b") == "R&B"
        assert proper_case_artist_name("rnb") == "RnB"
        assert proper_case_artist_name("R&B") == "R&B"
    
    def test_geographic_abbreviations(self):
        """Test geographic abbreviation handling."""
        assert proper_case_artist_name("uk garage") == "UK Garage"
        assert proper_case_artist_name("usa band") == "USA Band"
        assert proper_case_artist_name("us tour") == "US Tour"
        assert proper_case_artist_name("u.s.a band") == "U.S.A Band"
        assert proper_case_artist_name("u.s tour") == "U.S Tour"
    
    def test_roman_numerals(self):
        """Test Roman numeral handling."""
        assert proper_case_artist_name("album ii") == "Album II"
        assert proper_case_artist_name("volume iii") == "Volume III"
        assert proper_case_artist_name("part iv") == "Part IV"
        assert proper_case_artist_name("chapter v") == "Chapter V"
        assert proper_case_artist_name("book vi") == "Book VI"
        assert proper_case_artist_name("section vii") == "Section VII"
        assert proper_case_artist_name("act viii") == "Act VIII"
        assert proper_case_artist_name("scene ix") == "Scene IX"
        assert proper_case_artist_name("episode x") == "Episode X"
    
    def test_hyphenated_names(self):
        """Test hyphenated name handling."""
        assert proper_case_artist_name("jean-luc pierre") == "Jean-Luc Pierre"
        assert proper_case_artist_name("mary-jane watson") == "Mary-Jane Watson"
    
    def test_names_with_slashes(self):
        """Test names containing slashes."""
        assert proper_case_artist_name("artist/band") == "Artist/Band"
        assert proper_case_artist_name("ac/dc tribute") == "AC/DC Tribute"
    
    def test_empty_and_whitespace(self):
        """Test empty and whitespace-only inputs."""
        assert proper_case_artist_name("") == ""
        assert proper_case_artist_name("   ") == ""
        assert proper_case_artist_name("  philippe timsit  ") == "Philippe Timsit"
    
    def test_single_word(self):
        """Test single word names."""
        assert proper_case_artist_name("madonna") == "Madonna"
        assert proper_case_artist_name("prince") == "Prince"
        assert proper_case_artist_name("beyonce") == "Beyonce"
    
    def test_multiple_spaces(self):
        """Test names with multiple spaces."""
        # Note: Multiple spaces are normalized to single spaces
        assert proper_case_artist_name("philippe   timsit") == "Philippe Timsit"
        assert proper_case_artist_name("  john   doe  ") == "John Doe"
    
    def test_apostrophes(self):
        """Test names with apostrophes."""
        assert proper_case_artist_name("d'angelo") == "D'angelo"
        assert proper_case_artist_name("o'connor") == "O'connor"
    
    def test_real_world_artist_names(self):
        """Test with real-world artist names that might appear in metadata."""
        # French artists
        assert proper_case_artist_name("édith piaf") == "Édith Piaf"
        assert proper_case_artist_name("jacques brel") == "Jacques Brel"
        
        # International artists
        assert proper_case_artist_name("the beatles") == "The Beatles"
        assert proper_case_artist_name("pink floyd") == "Pink Floyd"
        assert proper_case_artist_name("led zeppelin") == "Led Zeppelin"
        
        # Artists with special formatting (periods are treated as word separators)
        # Note: Single letters after periods remain lowercase unless they're special cases
        assert proper_case_artist_name("k.d. lang") == "K.d. Lang"
        assert proper_case_artist_name("will.i.am") == "Will.i.am"


class TestArtistNameCapitalizationIntegration:
    """Integration tests for artist name capitalization in the creation process."""
    
    @pytest.mark.asyncio
    async def test_artist_creation_with_capitalization(self):
        """
        Test that artists are created with proper capitalization.
        
        This test verifies that when an artist name is provided in lowercase
        (as often happens with audio file metadata), it gets properly capitalized
        before being stored in the database.
        """
        # This would require mocking the GraphQL client and cache service
        # For now, we document the expected behavior
        pass
    
    @pytest.mark.asyncio
    async def test_artist_lookup_case_insensitive(self):
        """
        Test that artist lookup remains case-insensitive.
        
        This test verifies that existing artists can be found regardless of
        the case used in the search query.
        """
        # This would require mocking the GraphQL client and cache service
        # For now, we document the expected behavior
        pass
    
    @pytest.mark.asyncio
    async def test_normalization_logging(self, caplog):
        """
        Test that normalization is properly logged.
        
        When an artist name is normalized from lowercase to proper case,
        a log message should be generated for visibility.
        """
        # This would require mocking the GraphQL client and cache service
        # For now, we document the expected behavior
        pass


class TestEdgeCases:
    """Edge case tests for artist name handling."""
    
    def test_none_input(self):
        """Test handling of None input."""
        assert proper_case_artist_name(None) is None
    
    def test_numeric_input(self):
        """Test handling of numeric input (should not crash)."""
        # These should be handled gracefully
        try:
            result = proper_case_artist_name("123")
            assert result == "123"
        except (AttributeError, TypeError):
            pytest.fail("Function should handle numeric strings gracefully")
    
    def test_unicode_characters(self):
        """Test handling of unicode characters."""
        assert proper_case_artist_name("björk") == "Björk"
        assert proper_case_artist_name("sigur rós") == "Sigur Rós"
        assert proper_case_artist_name("mø") == "Mø"
    
    def test_special_characters(self):
        """Test handling of special characters."""
        assert proper_case_artist_name("depeche mode") == "Depeche Mode"
        assert proper_case_artist_name("bronski beat") == "Bronski Beat"
        assert proper_case_artist_name("pet shop boys") == "Pet Shop Boys"


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])
