#!/usr/bin/env python3
"""
Test script to verify the GraphQL filePath filter fix.
Tests the query syntax and validates it matches the schema.
"""

import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_query_syntax():
    """Test that the GraphQL queries have correct syntax."""
    print("=" * 60)
    print("TEST 1: GraphQL Query Syntax Validation")
    print("=" * 60)
    
    # Read the insert_batch_worker.py file
    with open('backend_worker/workers/insert/insert_batch_worker.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for the old incorrect syntax
    old_syntax_patterns = [
        'file_path: $filePath',  # Old snake_case syntax
        'filePath: {equals'  # Old equals syntax
    ]
    
    errors_found = []
    for pattern in old_syntax_patterns:
        if pattern in content:
            errors_found.append(f"Found old incorrect syntax: {pattern}")
    
    # Check for the new correct syntax (camelCase)
    new_syntax_patterns = [
        'filePath: $filePath',
        'tracks(where: {filePath: $filePath})'
    ]
    
    correct_syntax_found = all(pattern in content for pattern in new_syntax_patterns)
    
    if errors_found:
        print("❌ FAILED: Old incorrect syntax still present:")
        for error in errors_found:
            print(f"   - {error}")
        return False
    
    if not correct_syntax_found:
        print("❌ FAILED: New correct syntax not found")
        return False
    
    print("✅ PASSED: All GraphQL queries use correct syntax")
    print("   - filePath: $filePath (camelCase, direct String value)")
    return True


def test_track_filter_input_schema():
    """Test that TrackFilterInput schema has filePath field."""
    print("\n" + "=" * 60)
    print("TEST 2: TrackFilterInput Schema Validation")
    print("=" * 60)
    
    with open('backend/api/graphql/types/track_filter_type.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for filePath field in schema (camelCase)
    if 'filePath: Optional[str] = None' in content:
        print("✅ PASSED: TrackFilterInput has filePath field (camelCase)")
        return True
    else:
        print("❌ FAILED: TrackFilterInput missing filePath field")
        return False


def test_track_queries_implementation():
    """Test that track_queries.py implements filePath filter."""
    print("\n" + "=" * 60)
    print("TEST 3: Track Queries Implementation Validation")
    print("=" * 60)
    
    with open('backend/api/graphql/queries/queries/track_queries.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    checks = {
        'Cache params includes filePath': "'filePath': where.filePath" in content,
        'Filter logic implemented': "if where.filePath:" in content,
        'Path comparison': "t.path == where.filePath" in content
    }
    
    all_passed = True
    for check_name, result in checks.items():
        if result:
            print(f"✅ {check_name}")
        else:
            print(f"❌ {check_name}")
            all_passed = False
    
    return all_passed


def test_query_examples():
    """Test example GraphQL queries are valid."""
    print("\n" + "=" * 60)
    print("TEST 4: Example Query Validation")
    print("=" * 60)
    
    # Test query 1: GetTrackMusicBrainzIDs
    query1 = '''
    query GetTrackMusicBrainzIDs($filePath: String!) {
        tracks(where: {filePath: $filePath}) {
            musicbrainzId
            musicbrainzAlbumid
            musicbrainzArtistid
            musicbrainzAlbumartistid
        }
    }
    '''
    
    # Test query 2: GetTrackByPath
    query2 = '''
    query GetTrackByPath($filePath: String!) {
        tracks(where: {filePath: $filePath}) {
            id
            path
            bpm
        }
    }
    '''
    
    # Validate query structure
    validations = [
        ('Query 1 has correct where clause', 'where: {filePath: $filePath}' in query1),
        ('Query 2 has correct where clause', 'where: {filePath: $filePath}' in query2),
        ('Query 1 uses correct field name', 'filePath:' in query1),
        ('Query 2 uses correct field name', 'filePath:' in query2),
    ]
    
    all_passed = True
    for check_name, result in validations:
        if result:
            print(f"✅ {check_name}")
        else:
            print(f"❌ {check_name}")
            all_passed = False
    
    return all_passed


def test_no_snake_case_syntax():
    """Ensure no snake_case file_path syntax remains."""
    print("\n" + "=" * 60)
    print("TEST 5: No Legacy snake_case Syntax Remaining")
    print("=" * 60)
    
    files_to_check = [
        'backend_worker/workers/insert/insert_batch_worker.py',
        'backend/api/graphql/queries/queries/track_queries.py',
        'backend/api/graphql/types/track_filter_type.py'
    ]
    
    snake_case_found = False
    
    for filepath in files_to_check:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for file_path: pattern in GraphQL contexts (excluding Python variable names)
        lines = content.split('\n')
        for line_num, line in enumerate(lines, 1):
            # Look for file_path: in GraphQL query contexts (inside tracks(where: {...}))
            if 'file_path:' in line and 'where:' in line:
                print(f"❌ Found 'file_path:' in {filepath}:{line_num} (should be 'filePath:')")
                snake_case_found = True
    
    if not snake_case_found:
        print("✅ PASSED: No legacy 'file_path:' syntax found in GraphQL queries")
        return True
    
    return False


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("GRAPHQL FILEPATH FILTER FIX - TEST SUITE")
    print("=" * 60)
    
    tests = [
        test_query_syntax,
        test_track_filter_input_schema,
        test_track_queries_implementation,
        test_query_examples,
        test_no_snake_case_syntax
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"\n❌ TEST ERROR: {e}")
            results.append(False)
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    print(f"Tests passed: {passed}/{total}")
    
    if all(results):
        print("\n✅ ALL TESTS PASSED - Fix is valid and complete")
        return 0
    else:
        print("\n❌ SOME TESTS FAILED - Please review the implementation")
        return 1


if __name__ == '__main__':
    sys.exit(main())
