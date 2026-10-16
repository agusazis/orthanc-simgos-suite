<?php
namespace RIS\driver\worklist;

class ORTHANC extends Driver {
    protected function onBeforeKirim($params = []) {
        $id = $params["tindakanMedis"]["ID"];
        $studyUID = $this->generateUID($id);
        $this->zds->getFieldByName("StudyUUID")->set("VALUE", $studyUID);

        $this->obr->getFieldByName("FillerField1")->set("VALUE", $id);

        $logs = $params["logs"];
        if(count($logs) > 0) {
            if($logs[0]["STATUS"] == 1) {
                if($this->orc->getFieldByName("OrderControl")->get('VALUE') == "NW") {
                    $this->orc->getFieldByName("OrderControl")->set('VALUE', "XO");
                }
            }
        }
    }
}
