#include <VecGeom/base/Transformation3D.h>
#include <VecGeom/management/GeoManager.h>
#include "PTGeoTree.hh"

using namespace std;
std::vector<std::shared_ptr<Prompt::GeoTree::Node>> Prompt::GeoTree::Node::allPhysicalNodes = std::vector<std::shared_ptr<Prompt::GeoTree::Node>>{};

void Prompt::GeoTree::Node::print()
{
  std::cout << "node physicalID " << physical << ", logicalID " << logical << "\n";
  matrix.Print();
  if(!childPhysicalID.empty())
  {
    std::cout << "\nChild physical ID: ";
    for (const auto &c : childPhysicalID)
    {
      std::cout << c << "  ";
    }
    std::cout << "\n";
  }

  if(!child.empty())
  {
    std::cout << "Child physical and logical ID (from the child objects):\n";
    for (const auto &c : child)
    {
      std::cout << "[" << c->physical << ", ";
      std::cout << c->logical << "],  ";
    }
    std::cout << "\n";
  }
  std::cout << "\n";
}

void Prompt::GeoTree::Node::printAllNodes()
{
  for(auto node : allPhysicalNodes)
    node->print();
}

void Prompt::GeoTree::Node::clearAllNodes()
{
  allPhysicalNodes.clear();
}

void Prompt::GeoTree::Node::addChild(std::shared_ptr<Node> c)
{
  child.push_back(c);
}

void Prompt::GeoTree::Node::setMatrix(const vecgeom::Transformation3D *mat)
{
  matrix = mat->Inverse();
}

Prompt::GeoTree::GeoTree()
:m_root(std::make_shared<GeoTree::Node>())
{
  makeTree();
  printf("\n+++begin full tree node (physical)\n");
  printTree();
  printf("\n+++end full tree node (physical)\n\n");
}

Prompt::GeoTree::~GeoTree() {}

shared_ptr<Prompt::GeoTree::Node> Prompt::GeoTree::getRoot() { return m_root; }

vector<shared_ptr<Prompt::GeoTree::Node>> Prompt::GeoTree::findMotherNodeByPhysical(int num)
{
  auto motherNodes = vector<shared_ptr<GeoTree::Node>>();
  for(auto node : m_root->allPhysicalNodes)
  {
    if(std::find(node->childPhysicalID.begin(), node->childPhysicalID.end(), num) != node->childPhysicalID.end())
      motherNodes.push_back(node);
  }
  return motherNodes;
}

void Prompt::GeoTree::countChildNode(const std::shared_ptr<Prompt::GeoTree::Node> &node, unsigned &count)
{
  if(node->childPhysicalID.size()!=node->child.size())
    PROMPT_THROW2(BadInput, "Prompt::GeoTree::countChildNode node->childPhysicalID.size()!=node->child.size())");

  count += node->childPhysicalID.size();

  for(const auto &n : node->child)
  {
    countChildNode(n, count);
  }
}

void Prompt::GeoTree::updateChildMatrix(std::shared_ptr<Node> &node, const vecgeom::Transformation3D &motherMatrix)
{
  if(node->childPhysicalID.size()!=node->child.size())
    PROMPT_THROW2(BadInput, "Prompt::GeoTree::countChildNode node->childPhysicalID.size()!=node->child.size())");

  m_fullTreeNode.push_back(node);
  vecgeom::Transformation3D m = node->matrix ;
  m.MultiplyFromRight(motherMatrix);

  m_fllTreeMatrix.push_back(m);

  for(auto &cn : node->child)
  {
    updateChildMatrix(cn, m);
  }
}


// enum NODETYPE { PLACED, LOGICAL, FULL};
unsigned Prompt::GeoTree::getNumNodes(NODETYPE type)
{
  if(type==PLACED)
  {
    return m_root->allPhysicalNodes.size();
  }
  else if(type==FULL)
  {
    unsigned totvol = 1; // the world
    countChildNode(m_root, totvol);
     return totvol;
  }
  else if(type==LOGICAL)
  {
    PROMPT_THROW2(BadInput, "type==LOGICAL not yet impletemnted");
    return 0;
  }
  return 0;
}


void Prompt::GeoTree::makeTree()
{
  auto &geoManager = vecgeom::GeoManager::Instance();
  size_t pvolCnt = geoManager.GetPlacedVolumesCount();
  size_t vgtreenodecnt = geoManager.GetTotalNodeCount();
  printf("total volume in the tree %ld\n", vgtreenodecnt);
  printf("total placed volume %ld\n", pvolCnt);
  if(pvolCnt==0 && vgtreenodecnt==0)
    return;

  auto tree = this;
  auto world = geoManager.GetWorld();

  bool emforce_placement=false; // fixme: this parameter should be an optional

  if(world->id()!=(pvolCnt-1))
  PROMPT_THROW(BadInput, "world is not the last one in the volume vector");

  //update the info for the root
  auto root = tree->getRoot();
  root->physical = world->id();
  root->logical = world->GetLogicalVolume()->id();
  root->setMatrix(world->GetTransformation());
  for(auto d: world->GetDaughters())
  {
    root->childPhysicalID.push_back(d->id());
  }
  Prompt::GeoTree::Node::allPhysicalNodes.push_back(root);

  // pvolCnt-2, skip the world as it is the root
  for(size_t i=pvolCnt-2;i<-1;i--)
  {
    auto *vol = geoManager.Convert(i);


    auto node = std::shared_ptr<Prompt::GeoTree::Node>(new Prompt::GeoTree::Node {vol->id(), vol->GetLogicalVolume()->id()});
    node->setMatrix(vol->GetTransformation());
    // set daughters
    auto &dau = vol->GetDaughters();
    for(auto d: dau)
    {
      node->childPhysicalID.push_back(d->id());
    }
    // node->print();
    Prompt::GeoTree::Node::allPhysicalNodes.push_back(node);


    //set the correlation of this node to the tree
    auto mothers = tree->findMotherNodeByPhysical(i);
    if(mothers.empty())
    {
      if(emforce_placement)
        PROMPT_THROW(BadInput, "Mother volume is not found");
      continue;
    }
    for(auto m:mothers)
    {
      printf("Physical volume ID %zu, \"%s\" added into the geometry tree\n", i, vol->GetName());
      m->addChild(node);
    }
  }

  // update the matrix and also the m_fullTreeNode
  vecgeom::Transformation3D initialMat;
  updateChildMatrix(m_root, initialMat);

  //sanity test
  if(getNumNodes(PLACED) != geoManager.GetPlacedVolumesCount())
    PROMPT_THROW2(BadInput, getNumNodes(PLACED) << "getNumNodes(PLACED) != geoManager.GetPlacedVolumesCount() " << geoManager.GetPlacedVolumesCount());

  if(getNumNodes(FULL) != geoManager.GetTotalNodeCount())
    PROMPT_THROW2(BadInput, getNumNodes(FULL)  << "getNumNodes(FULL) != geoManager.GetTotalNodeCount()" << geoManager.GetTotalNodeCount());
}


std::vector<std::shared_ptr<Prompt::GeoTree::Node>> Prompt::GeoTree::findNode(int num, bool physical)
{
  auto nodes = vector<shared_ptr<GeoTree::Node>>();
  for(auto node : m_root->allPhysicalNodes)
  {
    if(physical ? node->physical : node->logical)
    {
      nodes.push_back(node);
    }
  }
  if(physical && nodes.size()>1)
    PROMPT_THROW(BadInput, "There are repeated physical nodes");

  return nodes;
}

void Prompt::GeoTree::print(const std::shared_ptr<Prompt::GeoTree::Node> &node, int layer, std::vector<std::vector<int>> &printArray, bool phys)
{
  try
  {
    if(phys)
      printArray.at(layer).push_back(node->physical);
    else
    {
      for(auto v: node->childPhysicalID)
        printArray.at(layer).push_back(v);
    }
  }
  catch (...)
  {
    printArray.push_back(vector<int>());
    if(phys)
      printArray.at(layer).push_back(node->physical);
    else
    {
      for(auto v: node->childPhysicalID)
        printArray.at(layer).push_back(v);
    }
  }
  for(auto pointptr: node->child)
  {
    print(pointptr,layer+1, printArray, phys);
  }
}

void Prompt::GeoTree::print(bool phys)
{
  vector<vector<int>> printArray;
  print(m_root, 0, printArray, phys);
  for(vector<int> varvector : printArray)
  {
    for(int var : varvector)
      cout << var << " ";
    cout << "\n";
  }
}

void Prompt::GeoTree::printTree()
{
  auto &geoManager = vecgeom::GeoManager::Instance();
  cout << "." << endl;
  printTreeRecursive(m_root, "", true);
}

void Prompt::GeoTree::printTreeRecursive(const shared_ptr<Node>& node, const string& prefix, bool isLast)
{
  if (!node) return;
  
  auto &geoManager = vecgeom::GeoManager::Instance();
  
  cout << prefix;
  if (isLast) {
    cout << "└── ";
  } else {
    cout << "├── ";
  }
  
  cout << getNodeName(node) << endl;
  
  string newPrefix = prefix;
  if (isLast) {
    newPrefix += "    ";
  } else {
    newPrefix += "│   ";
  }
  
  for (size_t i = 0; i < node->child.size(); ++i) {
    bool lastChild = (i == node->child.size() - 1);
    printTreeRecursive(node->child[i], newPrefix, lastChild);
  }
}

string Prompt::GeoTree::getNodeName(const shared_ptr<Node>& node)
{
  auto &geoManager = vecgeom::GeoManager::Instance();
  stringstream ss;
  
  try {
    auto *vol = geoManager.Convert(node->physical);
    if (vol) {
      string volName = vol->GetName();
      string logicalName = vol->GetLogicalVolume()->GetName();
      
      ss << "[" << node->physical << "] " << volName;
      
      if (!node->child.empty()) {
        ss << " [" << node->child.size() << " sub-nodes]";
      }
    }
  } catch (...) {
    ss << "[Invalid physical ID " << node->physical << "]";
  }
  
  return ss.str();
}