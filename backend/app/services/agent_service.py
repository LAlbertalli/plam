import re
from uuid import UUID
from sqlalchemy.orm import Session
from app.models.domain import Agent, Package, AgentPackage, Skill, MCPTool

class AgentService:
    def build_system_prompt(self, agent_id: UUID, db: Session) -> str:
        agent = db.query(Agent).filter(Agent.id == agent_id).first()
        if not agent:
            return ""
            
        system_prompt = agent.system_prompt
        
        # Load packages associated with this agent
        packages = db.query(Package).join(
            AgentPackage, AgentPackage.package_id == Package.id
        ).filter(
            AgentPackage.agent_id == agent_id
        ).all()
        
        if not packages:
            return system_prompt
            
        tools_str = ""
        skills_str = ""
        
        for pkg in packages:
            # Load skills
            skills = db.query(Skill).filter(Skill.package_id == pkg.id).all()
            for skill in skills:
                skills_str += f"\n- **{skill.name}**: {skill.description}\n"
                
            # Load MCP tools
            mcp_tools = db.query(MCPTool).filter(MCPTool.package_id == pkg.id).all()
            for tool in mcp_tools:
                tools_str += f"\n- **{tool.name}**: {tool.description}\n  Schema: {tool.mcp_schema}\n"
                
        injection = ""
        if skills_str:
            injection += f"\n### Available Sandbox Skills\nYou can invoke the following sandbox skills when executing commands:\n{skills_str}"
        if tools_str:
            injection += f"\n### Available MCP Tools\nYou can invoke the following MCP tools:\n{tools_str}"
            
        if injection:
            system_prompt += f"\n\n## Tools & Capabilities\n{injection}"
            
        return system_prompt

agent_service = AgentService()
