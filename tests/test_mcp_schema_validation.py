"""Test MCP schema improvements and validate JSON Schema correctness."""

import pytest
import json
from reviewer.mcp.server import ReviewerMCPServer


class TestMCPSchemaValidation:
    """Test that MCP schemas are valid and well-documented."""
    
    @pytest.mark.asyncio
    async def test_tool_schemas_are_valid(self):
        """Verify all tool schemas are valid JSON Schema."""
        server = ReviewerMCPServer()
        
        # Get tool list
        tools_response = await server.handle_tools_list({})
        tools = tools_response.get('tools', [])
        
        assert len(tools) == 5, "Should have 5 tools"
        
        for tool in tools:
            # Check required fields
            assert 'name' in tool
            assert 'description' in tool
            assert 'inputSchema' in tool
            
            # Validate the schema itself
            schema = tool['inputSchema']
            
            # Basic schema validation
            assert 'type' in schema
            assert schema['type'] == 'object'
            if 'properties' in schema:
                assert isinstance(schema['properties'], dict)
            
            # Check that descriptions are helpful
            assert len(tool['description']) > 20, f"Tool {tool['name']} should have detailed description"
            
            # Check property descriptions
            if 'properties' in schema:
                for prop_name, prop_def in schema['properties'].items():
                    assert 'description' in prop_def, f"Property {prop_name} in {tool['name']} should have description"
                    assert len(prop_def['description']) > 10, f"Property {prop_name} should have detailed description"
    
    @pytest.mark.asyncio
    async def test_required_fields_marked_clearly(self):
        """Verify required fields are clearly marked in descriptions."""
        server = ReviewerMCPServer()
        tools_response = await server.handle_tools_list({})
        tools = tools_response.get('tools', [])
        
        for tool in tools:
            schema = tool['inputSchema']
            required_fields = schema.get('required', [])
            
            if required_fields:
                properties = schema.get('properties', {})
                for field in required_fields:
                    if field in properties:
                        desc = properties[field].get('description', '')
                        # Check that required fields have [REQUIRED] marker
                        assert '[REQUIRED]' in desc, f"Required field {field} in {tool['name']} should be marked as [REQUIRED]"
    
    @pytest.mark.asyncio 
    async def test_enum_descriptions_have_details(self):
        """Verify enum fields have detailed explanations."""
        server = ReviewerMCPServer()
        tools_response = await server.handle_tools_list({})
        tools = tools_response.get('tools', [])
        
        for tool in tools:
            schema = tool['inputSchema']
            properties = schema.get('properties', {})
            
            for prop_name, prop_def in properties.items():
                if 'enum' in prop_def:
                    desc = prop_def.get('description', '')
                    # Enum descriptions should explain each option
                    for enum_val in prop_def['enum']:
                        if tool['name'] == 'review_changes' and prop_name == 'mode':
                            assert enum_val in desc, f"Enum value {enum_val} should be explained in description"
    
    @pytest.mark.asyncio
    async def test_pattern_validation_present(self):
        """Verify fields that need validation have patterns."""
        server = ReviewerMCPServer()
        tools_response = await server.handle_tools_list({})
        tools = tools_response.get('tools', [])
        
        # Fields that should have pattern validation
        pattern_fields = ['session_name']
        
        for tool in tools:
            schema = tool['inputSchema']
            properties = schema.get('properties', {})
            
            for field in pattern_fields:
                if field in properties:
                    assert 'pattern' in properties[field], f"Field {field} in {tool['name']} should have pattern validation"
    
    @pytest.mark.asyncio
    async def test_examples_provided_where_helpful(self):
        """Verify examples are provided for complex fields."""
        server = ReviewerMCPServer()
        tools_response = await server.handle_tools_list({})
        tools = tools_response.get('tools', [])
        
        # Fields that should have examples
        example_fields = ['directory']
        
        for tool in tools:
            if tool['name'] == 'review_changes':
                schema = tool['inputSchema']
                properties = schema.get('properties', {})
                
                for field in example_fields:
                    if field in properties:
                        assert 'examples' in properties[field], f"Field {field} should have examples"
                        assert len(properties[field]['examples']) > 0, f"Field {field} should have at least one example"
    
    @pytest.mark.asyncio
    async def test_mutually_exclusive_fields_documented(self):
        """Verify mutually exclusive fields are clearly documented."""
        server = ReviewerMCPServer()
        tools_response = await server.handle_tools_list({})
        tools = tools_response.get('tools', [])
        
        for tool in tools:
            if tool['name'] == 'review_changes':
                schema = tool['inputSchema']
                properties = schema.get('properties', {})
                
                # Check session_name and no_session are documented as mutually exclusive
                session_desc = properties.get('session_name', {}).get('description', '')
                no_session_desc = properties.get('no_session', {}).get('description', '')
                
                assert "Cannot be used with 'no_session'" in session_desc
                assert "Cannot be used with 'session_name'" in no_session_desc
    
    @pytest.mark.asyncio
    async def test_resource_descriptions_complete(self):
        """Verify resource descriptions explain the data format."""
        server = ReviewerMCPServer()
        resources_response = await server.handle_resources_list({})
        resources = resources_response.get('resources', [])
        
        assert len(resources) == 2, "Should have 2 resources"
        
        for resource in resources:
            assert 'uri' in resource
            assert 'name' in resource
            assert 'description' in resource
            assert 'mimeType' in resource
            
            # Descriptions should be detailed
            assert len(resource['description']) > 50, f"Resource {resource['uri']} should have detailed description"
            
            # Should mention data structure
            if resource['uri'] == 'review://sessions':
                assert 'JSON array' in resource['description']
                assert 'session includes' in resource['description']