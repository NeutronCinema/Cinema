#ifndef Prompt_GeoTree_hh
#define Prompt_GeoTree_hh

#include "PromptCore.hh"
#include "PTSingleton.hh"

#include <VecGeom/base/Transformation3D.h>

namespace Prompt {
  class GeoTree
  {
  public:
    struct Node {
      unsigned physical = -1, logical = -1;
      vecgeom::Transformation3D matrix;
      std::vector<std::shared_ptr<Node>> child;
      std::vector<unsigned> childPhysicalID;
      static std::vector<std::shared_ptr<Node>> allPhysicalNodes;

      void print();
      void printAllNodes();
      void clearAllNodes();
      void addChild(std::shared_ptr<Node> c);
      void setMatrix(const vecgeom::Transformation3D *mat);
    };


  public:
    GeoTree();
    ~GeoTree();

    void print(bool phys=true);
    void printTree();
    std::shared_ptr<Node> getRoot();
    std::vector<std::shared_ptr<Node>> findNode(int num, bool physical=true);
    void makeTree();
    //The placed are those defined by <physvol></physvol> in the gdml file
    //The logical are those defined by <volume></volume> in the gdml file
    //The full are those in the fully expended geometry tree
    enum NODETYPE { PLACED, LOGICAL, FULL};
    unsigned getNumNodes(NODETYPE type);
    std::vector<std::shared_ptr<Node>> m_fullTreeNode;
    std::vector<vecgeom::Transformation3D> m_fllTreeMatrix;

  private:
    friend class Singleton<GeoTree>;
    std::shared_ptr<Node> m_root;
    void countChildNode(const std::shared_ptr<Node> &node, unsigned &count);
    void updateChildMatrix(std::shared_ptr<Node> &node, const vecgeom::Transformation3D &motherMatrix);

    std::vector<std::shared_ptr<Node>> findMotherNodeByPhysical(int num);
    void print(const std::shared_ptr<Node> &node, int layer, std::vector<std::vector<int>> &printArray, bool phys);
    
    void printTreeRecursive(const std::shared_ptr<Node>& node, const std::string& prefix, bool isLast);
    std::string getNodeName(const std::shared_ptr<Node>& node);

  };

}


#endif